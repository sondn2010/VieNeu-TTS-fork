"""`python -m vieneu_portal <group> <command>` dispatch for the admin CLI
(distinct from `__main__.py`'s `serve`/`db` groups, which this module's
`main()` is wired into). Builds the argparse tree; each leaf subcommand sets
`handler=<fn>` via `set_defaults`, so `main()` only ever calls `args.handler(args)`.

Shared session/settings/moderation helpers live here (not in a sixth file)
since every command module needs them and none of them owns the concept.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

from sqlalchemy.orm import Session


def open_session() -> Session:
    from ..db.session_factory import get_sessionmaker

    return get_sessionmaker()()


def current_settings():
    from ..config import get_settings

    return get_settings()


def current_moderation(settings):
    from ..moderation.moderation_provider_factory import build_moderation_provider

    return build_moderation_provider(settings)


def _online_backup_sqlite(source_path: Path, dest_path: Path) -> None:
    """SQLite's own online-backup API (never a raw file copy): safe even
    while the old admin app (kept running until phase 6) still writes to the
    source in WAL mode.
    """
    src = sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(dest_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _handle_migrate_sqlite(args: argparse.Namespace) -> int:
    from ..db.database_backup_before_migrate import backup_before_upgrade
    from ..sqlite_migration.run_sqlite_to_postgres_migration import run_migration

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.is_file():
        print(f"no such file: {sqlite_path}", file=sys.stderr)
        return 1

    settings = current_settings()
    backup_dir = Path(settings.BACKUP_DIR)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    sqlite_backup_path = backup_dir / f"{sqlite_path.stem}-{stamp}.sqlite3"
    _online_backup_sqlite(sqlite_path, sqlite_backup_path)

    pg_dump_path = backup_before_upgrade(settings.DATABASE_URL, backup_dir, skip_backup=False)

    db = open_session()
    try:
        report = run_migration(
            db, settings, sqlite_path=sqlite_backup_path, apply=args.apply, allow_existing=args.allow_existing,
        )
    finally:
        db.close()
    report.backup_path = str(pg_dump_path) if pg_dump_path else None

    report_json = report.to_json()
    if args.report:
        Path(args.report).write_text(report_json, encoding="utf-8")
    print(report_json)
    print(f"\nSQLite online backup: {sqlite_backup_path}")
    return report.exit_code()


def _add_migrate_sqlite_parser(top_sub) -> None:
    parser = top_sub.add_parser("migrate-sqlite")
    parser.add_argument("--sqlite", required=True, help="path to the legacy admin.sqlite3")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", dest="apply", action="store_false")
    mode.add_argument("--apply", dest="apply", action="store_true")
    parser.add_argument("--report", help="also write the JSON report to this file")
    parser.add_argument(
        "--allow-existing", action="store_true",
        help="allow a target that already has users/packs without migration provenance "
             "(natural-key conflicts still abort)",
    )
    parser.set_defaults(handler=_handle_migrate_sqlite)


def register_admin_cli_commands(top_sub) -> None:
    """Adds every admin-CLI group (`migrate-sqlite`, `admin`, `user`,
    `system-dict`, `voices`, `text`) onto an existing top-level subparsers
    object. `__main__.py` calls this on its own subparsers, next to `serve`
    and `db`, so `python -m vieneu_portal <group> <command>` is one parser
    with one dispatch — not two separate CLIs.
    """
    from . import commands_system_dictionaries, commands_text_preview, commands_users_and_admins, commands_voices

    _add_migrate_sqlite_parser(top_sub)
    commands_users_and_admins.add_parsers(top_sub)
    commands_system_dictionaries.add_parsers(top_sub)
    commands_voices.add_parsers(top_sub)
    commands_text_preview.add_parsers(top_sub)


def build_parser() -> argparse.ArgumentParser:
    """Standalone parser with only the admin-CLI groups — convenient for
    testing this module in isolation from `serve`/`db`."""
    parser = argparse.ArgumentParser(prog="python -m vieneu_portal")
    top_sub = parser.add_subparsers(dest="group", required=True)
    register_admin_cli_commands(top_sub)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)
