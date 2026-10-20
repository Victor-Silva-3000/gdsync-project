# gdsync

[English](README.md) | **Português (Brasil)**

Envia um arquivo local para qualquer pasta do Google Drive. Se essa pasta já tiver um arquivo binário com o mesmo nome, o gdsync atualiza esse arquivo. Se o MD5 coincidir, o envio é ignorado.

Caminhos como `Work/2026` são resolvidos dentro do Meu Drive. Um id de pasta ou um link `drive.google.com/drive/folders/...` também funciona em drives compartilhados. Apelidos salvos deixam as pastas frequentes em uma palavra.

## Instalação

Python 3.10 ou mais novo. Instale em um ambiente virtual neste diretório. Debian, Ubuntu, Fedora e Arch atuais, e o Python do Homebrew, recusam `pip install` fora de um ambiente virtual.

O lançador grava um caminho absoluto para esse ambiente virtual. Se você mover o projeto, crie o ambiente virtual de novo, reinstale e atualize o link abaixo.

### Linux

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

### macOS

Instale o Python 3.10+ em [python.org](https://www.python.org/downloads/macos/) ou com `brew install python`. Depois use os mesmos comandos de ambiente virtual, `pip` e `ln` do Linux.

O macOS não coloca `~/.local/bin` no `PATH`. Adicione a linha `export` acima ao `~/.zshrc` e abra um terminal novo.

### Windows

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

## Faça login uma vez

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

## Sincronizar um arquivo

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

## Configuração

Troque o diretório de configuração com `--config-dir` ou `GDSYNC_CONFIG_DIR`.
