# gdsync

**English** | [Português (Brasil)](README.pt-BR.md)

Upload a local file into any Google Drive folder. If that folder already has a binary file with the same name, gdsync updates it. If the MD5 matches, it skips the upload.

Paths such as `Work/2026` are resolved inside My Drive. A folder id or a `drive.google.com/drive/folders/...` link also works for shared drives. Saved aliases make the common folders one word.

## Install

Python 3.10 or newer. Install into a virtualenv in this directory. Current Debian, Ubuntu, Fedora, Arch, and Homebrew Python refuse `pip install` outside one.

The launcher stores an absolute path to that virtualenv. If you move the project, create the virtualenv again and reinstall, then refresh the link below.

### Linux

Debian and Ubuntu ship the virtualenv module separately. Fedora and Arch include it with Python.

```bash
# Debian, Ubuntu
sudo apt install python3 python3-venv

# Fedora
sudo dnf install python3

# Arch
sudo pacman -S python
```

```bash
cd gdsync
python3 -m venv .venv
.venv/bin/pip install -e .
mkdir -p ~/.local/bin
ln -sf "$PWD/.venv/bin/gdsync" ~/.local/bin/gdsync
```

Open a new terminal and run `gdsync`. If the command is missing, `~/.local/bin` is not on `PATH`. Add this to `~/.bashrc` or `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### macOS

Install Python 3.10+ from [python.org](https://www.python.org/downloads/macos/) or with `brew install python`. Then use the same virtualenv, `pip`, and `ln` commands as on Linux.

macOS does not put `~/.local/bin` on `PATH`. Add the `export` line above to `~/.zshrc` and open a new terminal.

### Windows

Install Python 3.10+ from [python.org](https://www.python.org/downloads/windows/) and leave **Add python.exe to PATH** enabled. In PowerShell, from this directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\pip install -e .
$dir = Join-Path $env:USERPROFILE ".local\bin"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
New-Item -ItemType SymbolicLink -Force -Path (Join-Path $dir "gdsync.exe") -Target "$PWD\.venv\Scripts\gdsync.exe"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$dir*") {
    [Environment]::SetEnvironmentVariable("Path", "$dir;$userPath", "User")
}
```

`New-Item -ItemType SymbolicLink` needs Administrator or Developer Mode. Open a new terminal and run `gdsync`. If `py` is not found, use `python -m venv .venv` instead.

## Sign in once

1. In [Google Cloud Console](https://console.cloud.google.com/), enable the Google Drive API.
2. Configure the OAuth consent screen. While publishing status is Testing, open [Audience](https://console.cloud.google.com/auth/audience) and add the Google account you will sign in with under Test users. That account must be the one selected in the browser. Google's "only approved testers can access" message means this list is missing that address. While the app stays in Testing, the refresh token expires after 7 days; run `gdsync auth --reauth` again when that happens.
3. Create an OAuth client of type **Desktop app** and download the JSON.
4. Run:

```bash
gdsync auth --credentials ~/Downloads/client_secret.json
```

Examples below use `gdsync`. Without the link, prefix `.venv/bin/` on Linux and macOS, or `.\.venv\Scripts\` on Windows.

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
