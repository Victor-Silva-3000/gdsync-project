"""Upload-or-skip decision. No network."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping, Optional, Sequence

GOOGLE_NATIVE_PREFIX = "application/vnd.google-apps."


def file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_google_native(mime: str) -> bool:
    return mime.startswith(GOOGLE_NATIVE_PREFIX)


def choose_remote(files: Sequence[Mapping[str, str]]) -> Optional[dict]:
    if not files:
        return None
    return dict(max(files, key=lambda item: (item.get("modifiedTime") or "", item.get("id") or "")))


def select_sync_target(files: Sequence[Mapping[str, str]]) -> tuple[Optional[dict], list[dict], list[dict]]:
    binaries = [dict(item) for item in files if not is_google_native(item.get("mimeType") or "")]
    natives = [dict(item) for item in files if is_google_native(item.get("mimeType") or "")]
    return choose_remote(binaries), binaries, natives


def decide(local_md5: Optional[str], remote: Optional[Mapping[str, str]], force: bool, always_new: bool) -> str:
    if always_new or remote is None:
        return "create"
    remote_md5 = remote.get("md5Checksum")
    if not force and remote_md5 and local_md5 == remote_md5:
        return "skip"
    return "update"
