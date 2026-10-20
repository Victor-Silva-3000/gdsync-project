"""Command line for gdsync."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from gdsync import __version__
from gdsync.config import Config, default_config_dir
from gdsync.resolve import AmbiguousFolder, FolderNotFound, FolderSpecError


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help(sys.stderr)
        return 1
    config = Config(Path(args.config_dir) if args.config_dir else default_config_dir())
    try:
        return args.func(args, config)
    except KeyboardInterrupt:
        print("\ngdsync: interrupted", file=sys.stderr)
        return 130
    except (FolderSpecError, FolderNotFound, AmbiguousFolder) as exc:
        print(f"gdsync: {exc}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        if exc.code:
            print(exc.code, file=sys.stderr)
            return 1
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gdsync",
        description="Sync a local file into any Google Drive folder.",
    )
    parser.add_argument("--version", action="version", version=f"gdsync {__version__}")
    parser.add_argument(
        "--config-dir",
        help="config directory (default: $XDG_CONFIG_HOME/gdsync or ~/.config/gdsync)",
    )
    commands = parser.add_subparsers(dest="command")

    auth = commands.add_parser("auth", help="sign in with Google and store a refresh token")
    auth.add_argument("--credentials", type=Path, help="Desktop OAuth client JSON to copy into the config dir")
    auth.add_argument("--reauth", action="store_true", help="forget the saved token and sign in again")
    auth.add_argument("--no-browser", action="store_true", help="print the login URL instead of opening a browser")
    auth.set_defaults(func=cmd_auth)

    put = commands.add_parser(
        "put",
        help="upload files, or update them when the same name already exists in the folder",
    )
    put.add_argument("sources", nargs="+", help="local files, then the destination folder unless --to is set")
    put.add_argument("--to", "-t", help="folder alias, id, path, or Drive folder URL")
    put.add_argument("--name", help="remote file name (one local file only)")
    put.add_argument("--force", action="store_true", help="upload even when the Drive checksum matches")
    put.add_argument("--new", action="store_true", help="always create a new Drive file")
    put.add_argument("--mkdir", action="store_true", help="create missing folders when the destination is a path")
    put.add_argument("--dry-run", action="store_true", help="resolve the folder and say what would change")
    put.add_argument("--quiet", "-q", action="store_true", help="hide upload progress")
    put.add_argument("--json", action="store_true", help="print one JSON object per file")
    put.set_defaults(func=cmd_put)

    ls = commands.add_parser("ls", help="list a Drive folder")
    ls.add_argument("folder", nargs="?", default="root", help="alias, id, path, or URL (default: My Drive root)")
    ls.set_defaults(func=cmd_ls)

    alias = commands.add_parser("alias", help="short names for folders")
    alias_cmds = alias.add_subparsers(dest="alias_command")
    alias_set = alias_cmds.add_parser("set", help="save a folder alias")
    alias_set.add_argument("name")
    alias_set.add_argument("folder", help="folder id, path, or URL")
    alias_set.set_defaults(func=cmd_alias_set)
    alias_rm = alias_cmds.add_parser("rm", help="delete an alias")
    alias_rm.add_argument("name")
    alias_rm.set_defaults(func=cmd_alias_rm)
    alias_ls = alias_cmds.add_parser("ls", help="list aliases")
    alias_ls.set_defaults(func=cmd_alias_ls)
    alias.set_defaults(func=cmd_alias_ls)
    return parser


def split_sources_dest(sources: list[str], to: str | None) -> tuple[list[str], str]:
    if to is not None:
        if not sources:
            raise FolderSpecError("need at least one local file")
        return sources, to
    if len(sources) < 2:
        raise FolderSpecError("need a destination folder. Example: gdsync put notes.txt invoices")
    return sources[:-1], sources[-1]


def cmd_auth(args, config: Config) -> int:
    from gdsync.auth import get_credentials, install_credentials
    from gdsync.drive import DriveError, about_user, build_service

    try:
        if args.credentials:
            install_credentials(config, args.credentials)
        creds = get_credentials(config, reauth=args.reauth, no_browser=args.no_browser)
        account = about_user(build_service(creds))
    except DriveError as exc:
        print(f"gdsync: {exc}", file=sys.stderr)
        return 2
    print(f"signed in as {account}")
    print(f"token: {config.token_path}")
    return 0


def cmd_put(args, config: Config) -> int:
    from gdsync.auth import get_credentials
    from gdsync.drive import DriveError, build_service, sync_file

    sources, dest = split_sources_dest(list(args.sources), args.to)
    if args.name and len(sources) != 1:
        print("gdsync: --name applies to a single file", file=sys.stderr)
        return 1
    try:
        service = build_service(get_credentials(config))
        for source in sources:
            progress = _Progress(Path(source).name, enabled=not args.quiet and not args.json)
            try:
                result = sync_file(
                    service,
                    Path(source).expanduser(),
                    dest,
                    config.aliases(),
                    remote_name=args.name,
                    force=args.force,
                    always_new=args.new,
                    mkdir=args.mkdir,
                    dry_run=args.dry_run,
                    progress=progress,
                )
            finally:
                progress.finish()
            _print_result(result, json_mode=args.json)
    except DriveError as exc:
        print(f"gdsync: {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_ls(args, config: Config) -> int:
    from gdsync.auth import get_credentials
    from gdsync.drive import DriveError, build_service, list_folder

    try:
        service = build_service(get_credentials(config))
        _folder_id, rows = list_folder(service, args.folder, config.aliases())
    except DriveError as exc:
        print(f"gdsync: {exc}", file=sys.stderr)
        return 2
    for row in rows:
        kind = "dir" if row.get("mimeType") == "application/vnd.google-apps.folder" else "file"
        print(f"{row.get('id', '')}\t{kind}\t{row.get('name', '')}")
    return 0


def cmd_alias_set(args, config: Config) -> int:
    stored = config.set_alias(args.name, args.folder)
    print(f"{args.name}\t{stored}")
    return 0


def cmd_alias_rm(args, config: Config) -> int:
    config.remove_alias(args.name)
    return 0


def cmd_alias_ls(args, config: Config) -> int:
    if getattr(args, "alias_command", None) not in (None, "ls"):
        print("gdsync: unknown alias command", file=sys.stderr)
        return 1
    for name, target in sorted(config.aliases().items()):
        print(f"{name}\t{target}")
    return 0


def _print_result(result, *, json_mode: bool) -> None:
    if result.warning:
        print(f"gdsync: {result.warning}", file=sys.stderr)
    if json_mode:
        print(json.dumps(asdict(result), ensure_ascii=False))
        return
    ident = f"  {result.file_id}" if result.file_id else ""
    link = f"  {result.link}" if result.link else ""
    print(f"{result.action:13}  {result.name}{ident}{link}")


class _Progress:
    def __init__(self, label: str, *, enabled: bool):
        self.label = label
        self.enabled = enabled
        self.started = False

    def __call__(self, fraction: float) -> None:
        if not self.enabled:
            return
        self.started = True
        print(f"\r{self.label}  {int(fraction * 100):3d}%", end="", file=sys.stderr, flush=True)

    def finish(self) -> None:
        if self.started:
            print(file=sys.stderr)
