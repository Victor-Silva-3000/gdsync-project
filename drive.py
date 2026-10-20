"""Google Drive calls: resolve a folder, then create or update one file."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from gdsync.plan import decide, file_md5, select_sync_target
from gdsync.resolve import (
    FOLDER_MIME,
    AmbiguousFolder,
    FolderNotFound,
    FolderSpecError,
    child_list_query,
    classify_folder,
    file_query,
    folder_query,
    resolve_target,
)

Progress = Callable[[float], None]
LIST_FIELDS = "nextPageToken,files(id,name,mimeType,md5Checksum,modifiedTime,size,webViewLink)"
CHUNK = 8 * 1024 * 1024


class DriveError(RuntimeError):
    pass


@dataclass
class SyncResult:
    action: str
    name: str
    local: str
    file_id: Optional[str] = None
    link: Optional[str] = None
    warning: Optional[str] = None


def build_service(creds):
    _, _, _, discovery, _, _ = _libs()
    return discovery.build("drive", "v3", credentials=creds, cache_discovery=False)


def about_user(service) -> str:
    try:
        payload = service.about().get(fields="user(displayName,emailAddress)").execute()
    except Exception as exc:
        _reraise(exc)
    user = payload.get("user") or {}
    name = user.get("displayName") or ""
    email = user.get("emailAddress") or ""
    if name and email:
        return f"{name} <{email}>"
    return email or name or "unknown account"


def list_folder(service, folder_spec: str, aliases: dict) -> tuple[str, list[dict]]:
    folder_id = _resolve_folder(service, folder_spec, aliases, mkdir=False)
    folder_id, ctx = _folder_context(service, folder_id)
    rows = _list(service, child_list_query(folder_id), ctx)
    rows.sort(key=lambda item: (0 if item.get("mimeType") == FOLDER_MIME else 1, (item.get("name") or "").lower()))
    return folder_id, rows


def sync_file(
    service,
    local: Path,
    folder_spec: str,
    aliases: dict,
    *,
    remote_name: Optional[str] = None,
    force: bool = False,
    always_new: bool = False,
    mkdir: bool = False,
    dry_run: bool = False,
    progress: Optional[Progress] = None,
) -> SyncResult:
    if not local.is_file():
        raise DriveError(f"not a file: {local}")
    name = remote_name or local.name
    folder_id = _resolve_folder(service, folder_spec, aliases, mkdir=mkdir)
    folder_id, ctx = _folder_context(service, folder_id)

    warning = None
    target = None
    if not always_new:
        matches = _list(service, file_query(folder_id, name), ctx)
        target, binaries, natives = select_sync_target(matches)
        if target is None and natives:
            raise DriveError(
                f"{name}: a Google Docs item with that name is already in the folder; "
                "pass --name or --new to upload a binary file beside it"
            )
        if len(binaries) > 1 and target is not None:
            warning = f"several files named {name}; updating the newest ({target['id']})"

    local_hash = file_md5(local) if target is not None else None
    action = decide(local_hash, target, force, always_new)
    if action == "skip" or dry_run:
        shown = action if action == "skip" else f"would-{action}"
        return SyncResult(
            action=shown,
            name=name,
            local=str(local),
            file_id=None if target is None else target.get("id"),
            link=None if target is None else target.get("webViewLink"),
            warning=warning,
        )

    uploaded = _upload(service, local, name, folder_id, target["id"] if action == "update" else None, progress)
    return SyncResult(
        action=action,
        name=uploaded.get("name") or name,
        local=str(local),
        file_id=uploaded.get("id"),
        link=uploaded.get("webViewLink"),
        warning=warning,
    )


def _resolve_folder(service, folder_spec: str, aliases: dict, *, mkdir: bool) -> str:
    target = classify_folder(folder_spec, aliases)
    ctx_box = {"ctx": None}

    def find_folders(parent_id: str, name: str):
        if ctx_box["ctx"] is None:
            _resolved, ctx_box["ctx"] = _folder_context(service, parent_id)
        return _list(service, folder_query(parent_id, name), ctx_box["ctx"])

    def make_dir(parent_id: str, name: str) -> str:
        body = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
        try:
            created = (
                service.files()
                .create(body=body, fields="id", supportsAllDrives=True)
                .execute(num_retries=3)
            )
        except Exception as exc:
            _reraise(exc)
        return created["id"]

    try:
        return resolve_target(target, find_folders, make_dir if mkdir else None)
    except (FolderNotFound, AmbiguousFolder, FolderSpecError, DriveError):
        raise
    except Exception as exc:
        _reraise(exc)


def _folder_context(service, folder_id: str, seen: Optional[set] = None) -> tuple[str, dict]:
    if folder_id == "root":
        return "root", {"corpora": "user"}
    seen = set() if seen is None else seen
    if folder_id in seen:
        raise DriveError(f"shortcut cycle at {folder_id}")
    seen.add(folder_id)
    try:
        meta = (
            service.files()
            .get(
                fileId=folder_id,
                fields="id,name,mimeType,driveId,shortcutDetails",
                supportsAllDrives=True,
            )
            .execute(num_retries=3)
        )
    except Exception as exc:
        _reraise(exc)

    if meta.get("mimeType") == "application/vnd.google-apps.shortcut":
        target_id = (meta.get("shortcutDetails") or {}).get("targetId")
        if not target_id:
            raise DriveError(f"{folder_id} is a shortcut with no target")
        return _folder_context(service, target_id, seen)

    if meta.get("mimeType") != FOLDER_MIME:
        label = meta.get("name") or folder_id
        raise DriveError(f"{label} is not a folder")

    if meta.get("driveId"):
        return folder_id, {
            "corpora": "drive",
            "driveId": meta["driveId"],
            "includeItemsFromAllDrives": True,
        }
    return folder_id, {"corpora": "user"}


def _list(service, query: str, ctx: dict) -> list[dict]:
    rows: list[dict] = []
    page_token = None
    while True:
        kwargs = {
            "q": query,
            "pageSize": 100,
            "fields": LIST_FIELDS,
            "supportsAllDrives": True,
            **ctx,
        }
        if page_token:
            kwargs["pageToken"] = page_token
        try:
            payload = service.files().list(**kwargs).execute(num_retries=3)
        except Exception as exc:
            _reraise(exc)
        rows.extend(payload.get("files") or [])
        page_token = payload.get("nextPageToken")
        if not page_token:
            return rows


def _upload(service, local: Path, name: str, folder_id: str, file_id: Optional[str], progress: Optional[Progress]):
    _, _, _, _, _, http = _libs()
    mime, _ = mimetypes.guess_type(local.name)
    resumable = local.stat().st_size > 5 * 1024 * 1024
    media = http.MediaFileUpload(str(local), mimetype=mime or "application/octet-stream", resumable=resumable, chunksize=CHUNK)
    try:
        if file_id:
            request = service.files().update(
                fileId=file_id,
                media_body=media,
                fields="id,name,webViewLink,md5Checksum,size",
                supportsAllDrives=True,
            )
        else:
            request = service.files().create(
                body={"name": name, "parents": [folder_id]},
                media_body=media,
                fields="id,name,webViewLink,md5Checksum,size",
                supportsAllDrives=True,
            )
        if not resumable:
            uploaded = request.execute(num_retries=3)
            if progress:
                progress(1.0)
            return uploaded
        uploaded = None
        while uploaded is None:
            status, uploaded = request.next_chunk(num_retries=3)
            if progress and status is not None:
                progress(status.progress())
        if progress:
            progress(1.0)
        return uploaded
    except Exception as exc:
        _reraise(exc)


def _libs():
    from gdsync.deps import load

    return load()


def _reraise(exc: Exception) -> None:
    if isinstance(exc, (DriveError, FolderNotFound, AmbiguousFolder, FolderSpecError, SystemExit, KeyboardInterrupt)):
        raise exc
    status = getattr(getattr(exc, "resp", None), "status", None)
    reason = getattr(exc, "reason", None) or str(exc)
    if status:
        raise DriveError(f"Google Drive API {status}: {reason}") from exc
    if exc.__class__.__name__ in {"HttpError", "RefreshError"}:
        raise DriveError(f"Google Drive API: {reason}") from exc
    raise exc
