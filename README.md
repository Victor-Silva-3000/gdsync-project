# gdsync

[English](#english) | [Português (Brasil)](#português-brasil)

## English

Upload a local file into any Google Drive folder. If that folder already has a binary file with the same name, gdsync updates it. If the MD5 matches, it skips the upload.

Paths such as `Work/2026` are resolved inside My Drive. A folder id or a `drive.google.com/drive/folders/...` link also works for shared drives. Saved aliases make the common folders one word.

### Install

Python 3.10 or newer. Install into a virtualenv in this directory. Current Debian, Ubuntu, Fedora, Arch, and Homebrew Python refuse `pip install` outside one.

The launcher stores an absolute path to that virtualenv. If you move the project, create the virtualenv again and reinstall, then refresh the link below.

#### Linux

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

#### macOS

Install Python 3.10+ from [python.org](https://www.python.org/downloads/macos/) or with `brew install python`. Then use the same virtualenv, `pip`, and `ln` commands as on Linux.

macOS does not put `~/.local/bin` on `PATH`. Add the `export` line above to `~/.zshrc` and open a new terminal.

#### Windows

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

### Sign in once

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

### Sync a file

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

### Config

Override the config directory with `--config-dir` or `GDSYNC_CONFIG_DIR`.

## Português (Brasil)

Envia um arquivo local para qualquer pasta do Google Drive. Se essa pasta já tiver um arquivo binário com o mesmo nome, o gdsync atualiza esse arquivo. Se o MD5 coincidir, o envio é ignorado.

Caminhos como `Work/2026` são resolvidos dentro do Meu Drive. Um id de pasta ou um link `drive.google.com/drive/folders/...` também funciona em drives compartilhados. Apelidos salvos deixam as pastas frequentes em uma palavra.

### Instalação

Python 3.10 ou mais novo. Instale em um ambiente virtual neste diretório. Debian, Ubuntu, Fedora e Arch atuais, e o Python do Homebrew, recusam `pip install` fora de um ambiente virtual.

O lançador grava um caminho absoluto para esse ambiente virtual. Se você mover o projeto, crie o ambiente virtual de novo, reinstale e atualize o link abaixo.

#### Linux

Debian e Ubuntu distribuem o módulo de ambiente virtual à parte. Fedora e Arch o incluem com o Python.

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

Abra um terminal novo e rode `gdsync`. Se o comando não for encontrado, `~/.local/bin` não está no `PATH`. Adicione isto ao `~/.bashrc` ou ao `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

#### macOS

Instale o Python 3.10+ em [python.org](https://www.python.org/downloads/macos/) ou com `brew install python`. Depois use os mesmos comandos de ambiente virtual, `pip` e `ln` do Linux.

O macOS não coloca `~/.local/bin` no `PATH`. Adicione a linha `export` acima ao `~/.zshrc` e abra um terminal novo.

#### Windows

Instale o Python 3.10+ em [python.org](https://www.python.org/downloads/windows/) e deixe **Add python.exe to PATH** marcado. No PowerShell, neste diretório:

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

`New-Item -ItemType SymbolicLink` exige Administrador ou Modo de Desenvolvedor. Abra um terminal novo e rode `gdsync`. Se `py` não for encontrado, use `python -m venv .venv`.

### Faça login uma vez

1. No [Google Cloud Console](https://console.cloud.google.com/), ative a API Google Drive.
2. Configure a tela de consentimento OAuth. Enquanto o status de publicação for Teste, abra [Público](https://console.cloud.google.com/auth/audience) e adicione a conta Google com a qual você vai entrar em Usuários de teste. Essa conta precisa ser a selecionada no navegador. A mensagem do Google "only approved testers can access" significa que essa lista não contém esse endereço. Enquanto o app permanecer em Teste, o refresh token expira depois de 7 dias; rode `gdsync auth --reauth` de novo quando isso acontecer.
3. Crie um cliente OAuth do tipo **App para computador** e baixe o JSON.
4. Rode:

```bash
gdsync auth --credentials ~/Downloads/client_secret.json
```

Os exemplos abaixo usam `gdsync`. Sem o link, use o prefixo `.venv/bin/` no Linux e no macOS, ou `.\.venv\Scripts\` no Windows.

O arquivo do cliente e o refresh token ficam em `~/.config/gdsync/` (ou `$XDG_CONFIG_HOME/gdsync`). Só o seu usuário consegue ler o token.

O app pede o escopo `drive` para gravar em pastas que já existem.

### Sincronizar um arquivo

```bash
gdsync alias set invoices 'https://drive.google.com/drive/folders/FOLDER_ID'
gdsync put report.pdf invoices
gdsync put ./out/*.pdf --to 'Work/2026' --mkdir
gdsync put notes.txt --to 1AbCdefGhijkLmnoPqrstuvwx --dry-run
```

`gdsync put` trata o último argumento como a pasta quando `--to` é omitido, como o `cp`.

| Resultado | Significado |
| --- | --- |
| `create` | a pasta não tinha arquivo binário com esse nome |
| `update` | já existia o mesmo nome e os bytes eram diferentes |
| `skip` | o MD5 no Drive já coincide com o arquivo local |
| `would-create` / `would-update` | `--dry-run` |

Outras flags: `--force` envia mesmo quando o checksum coincide, `--new` sempre cria outro arquivo, `--name` define o nome remoto, `--json` imprime um objeto por arquivo.

```bash
gdsync ls invoices
gdsync alias ls
```

### Configuração

Troque o diretório de configuração com `--config-dir` ou `GDSYNC_CONFIG_DIR`.
