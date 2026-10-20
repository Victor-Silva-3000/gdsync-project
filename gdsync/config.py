"""Aliases and OAuth client path under the config directory."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from gdsync.resolve import FolderSpecError, canonical_alias_value

_ALIAS_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def default_config_dir() -> Path:
    override = os.environ.get("GDSYNC_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "gdsync"


class Config:
    def __init__(self, directory: Path):
        self.directory = directory
        self.path = directory / "config.json"
        self.credentials_path = directory / "credentials.json"
        self.token_path = directory / "token.json"

    def load(self) -> dict:
        if not self.path.exists():
            return {"aliases": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data.setdefault("aliases", {})
        return data

    def save(self, data: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, indent=2) + "\n"
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(self.path)

    def aliases(self) -> dict[str, str]:
        raw = self.load().get("aliases") or {}
        return {str(key): str(value) for key, value in raw.items()}

    def set_alias(self, name: str, target: str) -> str:
        if not _ALIAS_NAME.fullmatch(name):
            raise FolderSpecError(
                "alias name must start with a letter or digit and use only "
                "letters, digits, '.', '_' or '-'"
            )
        stored = canonical_alias_value(target)
        data = self.load()
        data.setdefault("aliases", {})
        data["aliases"][name] = stored
        self.save(data)
        return stored

    def remove_alias(self, name: str) -> None:
        data = self.load()
        aliases = data.get("aliases") or {}
        if name not in aliases:
            raise FolderSpecError(f"no alias named {name}")
        del aliases[name]
        data["aliases"] = aliases
        self.save(data)
