"""Desktop OAuth for Google Drive. Token stays in the config directory."""

from __future__ import annotations

import shutil
from pathlib import Path

from gdsync.config import Config
from gdsync.deps import load

SCOPES = ["https://www.googleapis.com/auth/drive"]

MISSING_CLIENT = """No OAuth client file at {path}

1. In Google Cloud Console, enable the Google Drive API.
2. Configure the OAuth consent screen. If the app stays in Testing, add your Google account as a test user.
3. Create an OAuth client of type Desktop app and download its JSON.
4. Run:
     gdsync auth --credentials /path/to/client_secret.json
"""


def install_credentials(config: Config, source: Path) -> None:
    source = source.expanduser()
    if not source.is_file():
        raise SystemExit(f"OAuth client file not found: {source}")
    config.directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, config.credentials_path)
    config.credentials_path.chmod(0o600)


def get_credentials(config: Config, *, reauth: bool = False, no_browser: bool = False):
    transport, oauth_credentials, flow_mod, _, _, _ = load()
    if reauth and config.token_path.exists():
        config.token_path.unlink()

    creds = None
    if config.token_path.exists():
        creds = oauth_credentials.Credentials.from_authorized_user_file(str(config.token_path), SCOPES)

    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(transport.Request())
        _write_token(config, creds)
        return creds
    if not config.credentials_path.is_file():
        raise SystemExit(MISSING_CLIENT.format(path=config.credentials_path))

    flow = flow_mod.InstalledAppFlow.from_client_secrets_file(str(config.credentials_path), SCOPES)
    creds = flow.run_local_server(
        port=0,
        open_browser=not no_browser,
        access_type="offline",
        prompt="consent",
    )
    _write_token(config, creds)
    return creds


def _write_token(config: Config, creds) -> None:
    config.directory.mkdir(parents=True, exist_ok=True)
    config.token_path.write_text(creds.to_json(), encoding="utf-8")
    config.token_path.chmod(0o600)
