# gdsync

Upload a local file into any Google Drive folder. If that folder already has a binary file with the same name, gdsync updates it. If the MD5 matches, it skips the upload.

Paths such as `Work/2026` are resolved inside My Drive. A folder id or a `drive.google.com/drive/folders/...` link also works for shared drives. Saved aliases make the common folders one word.

## Install

Arch and other PEP 668 systems reject `python -m pip install` outside a virtualenv. Create one in this directory:

```bash
cd gdsync
python -m venv .venv
.venv/bin/pip install -e .
```

Run it as `.venv/bin/gdsync`. To call `gdsync` from anywhere, link it onto your user path:

```bash
mkdir -p ~/.local/bin
ln -sf "$PWD/.venv/bin/gdsync" ~/.local/bin/gdsync
```

## Sign in once

1. In [Google Cloud Console](https://console.cloud.google.com/), enable the Google Drive API.
2. Configure the OAuth consent screen. While publishing status is Testing, open [Audience](https://console.cloud.google.com/auth/audience) and add the Google account you will sign in with under Test users. That account must be the one selected in the browser. Google's "only approved testers can access" message means this list is missing that address. While the app stays in Testing, the refresh token expires after 7 days; run `gdsync auth --reauth` again when that happens.
3. Create an OAuth client of type **Desktop app** and download the JSON.
4. Run:

```bash
gdsync auth --credentials ~/Downloads/client_secret.json
```

Examples below use `gdsync`. If you skipped the link, prefix `.venv/bin/`.

The client file and refresh token are stored in `~/.config/gdsync/` (or `$XDG_CONFIG_HOME/gdsync`). The token is readable only by your user.

The app requests the `drive` scope so it can write into folders that already exist.

## Sync a file

```bash
gdsync alias set invoices 'https://drive.google.com/drive/folders/FOLDER_ID'
gdsync put report.pdf invoices
gdsync put ./out/*.pdf --to 'Work/2026' --mkdir
gdsync put notes.txt --to 1AbCdefGhijkLmnoPqrstuvwx --dry-run
```

`gdsync put` treats the last argument as the folder when `--to` is omitted, same as `cp`.

| Result | Meaning |
| --- | --- |
| `create` | folder had no binary file with that name |
| `update` | same name existed and the bytes differed |
| `skip` | Drive MD5 already matches the local file |
| `would-create` / `would-update` | `--dry-run` |

Other flags: `--force` uploads even when the checksum matches, `--new` always creates another file, `--name` sets the remote name, `--json` prints one object per file.

```bash
gdsync ls invoices
gdsync alias ls
```

## Config

Override the config directory with `--config-dir` or `GDSYNC_CONFIG_DIR`.
