"""Folder specs and Drive query strings. No network."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence

ID_RE = re.compile(r"^[A-Za-z0-9_-]{25,}$")
FOLDER_MIME = "application/vnd.google-apps.folder"
_FOLDERS_URL = re.compile(r"/folders/([A-Za-z0-9_-]+)")
_QUERY_ID = re.compile(r"[?&]id=([A-Za-z0-9_-]+)")
_FILE_URL = re.compile(
    r"(?:/file/d/|docs\.google\.com/(?:document|spreadsheets|presentation)/d/)"
)


class FolderSpecError(ValueError):
    pass


class FolderNotFound(LookupError):
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"folder not found: {path}")


class AmbiguousFolder(LookupError):
    def __init__(self, path: str, ids: Sequence[str]):
        self.path = path
        self.ids = list(ids)
        joined = ", ".join(self.ids)
        super().__init__(f"several folders named {path}: {joined}")


@dataclass(frozen=True)
class FolderTarget:
    kind: str  # "id" or "path"
    value: str


def escape_query(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise FolderSpecError("name cannot contain a newline")
    return value.replace("\\", "\\\\").replace("'", "\\'")


def extract_folder_id(spec: str) -> Optional[str]:
    if "google.com" not in spec:
        return None
    if _FILE_URL.search(spec):
        raise FolderSpecError(
            "link points at a file; paste a folder link "
            "(drive.google.com/drive/folders/...)"
        )
    match = _FOLDERS_URL.search(spec)
    if match:
        return match.group(1)
    match = _QUERY_ID.search(spec)
    if match:
        return match.group(1)
    raise FolderSpecError("could not read a folder id from that Google link")


def classify_folder(spec: str, aliases: Optional[Mapping[str, str]] = None) -> FolderTarget:
    text = spec.strip()
    if not text:
        raise FolderSpecError("empty folder")
    if text in ("/", "root"):
        return FolderTarget("id", "root")

    folder_id = extract_folder_id(text)
    if folder_id:
        return FolderTarget("id", folder_id)

    if aliases and text in aliases:
        return classify_folder(aliases[text], aliases=None)

    if text.startswith("id:"):
        ident = text[3:].strip()
        if not ident:
            raise FolderSpecError("empty folder id")
        return FolderTarget("id", ident)
    if text.startswith("path:"):
        path = text[5:].strip()
        split_path(path)
        return FolderTarget("path", path)

    if "/" in text or "\\" in text:
        path = text.replace("\\", "/")
        split_path(path)
        return FolderTarget("path", path)
    if ID_RE.fullmatch(text):
        return FolderTarget("id", text)
    return FolderTarget("path", text)


def canonical_alias_value(spec: str) -> str:
    target = classify_folder(spec, aliases=None)
    if target.kind == "id":
        return f"id:{target.value}"
    return f"path:{target.value}"


def split_path(path: str) -> list[str]:
    parts: list[str] = []
    for part in path.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise FolderSpecError("folder path cannot contain '..'")
        parts.append(part)
    return parts


def folder_query(parent_id: str, name: str) -> str:
    return " and ".join(
        [
            f"name = '{escape_query(name)}'",
            f"'{escape_query(parent_id)}' in parents",
            "trashed = false",
            f"mimeType = '{FOLDER_MIME}'",
        ]
    )


def file_query(parent_id: str, name: str) -> str:
    return " and ".join(
        [
            f"name = '{escape_query(name)}'",
            f"'{escape_query(parent_id)}' in parents",
            "trashed = false",
            f"mimeType != '{FOLDER_MIME}'",
        ]
    )


def child_list_query(parent_id: str) -> str:
    return " and ".join(
        [
            f"'{escape_query(parent_id)}' in parents",
            "trashed = false",
        ]
    )


def resolve_path(
    parts: Sequence[str],
    find_folders: Callable[[str, str], Sequence[Mapping[str, str]]],
    mkdir: Optional[Callable[[str, str], str]] = None,
) -> str:
    parent = "root"
    walked: list[str] = []
    for part in parts:
        walked.append(part)
        label = "/".join(walked)
        matches = list(find_folders(parent, part))
        if len(matches) > 1:
            raise AmbiguousFolder(label, [item["id"] for item in matches])
        if len(matches) == 1:
            parent = matches[0]["id"]
            continue
        if mkdir is None:
            raise FolderNotFound(label)
        parent = mkdir(parent, part)
    return parent


def resolve_target(
    target: FolderTarget,
    find_folders: Callable[[str, str], Sequence[Mapping[str, str]]],
    mkdir: Optional[Callable[[str, str], str]] = None,
) -> str:
    if target.kind == "id":
        return target.value
    parts = split_path(target.value)
    if not parts:
        return "root"
    return resolve_path(parts, find_folders, mkdir)
