"""CLI entry: `python -m vieneu_portal serve|worker|db upgrade|db current|
migrate-sqlite|admin|user|system-dict|voices|text` (the last six groups are
the admin CLI, registered by `admin_cli.cli_parser_and_dispatch`)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

PACKAGE_DIR = Path(__file__).resolve().parent


def _serve() -> None:
    import uvicorn

    from .config import get_settings

    settings = get_settings()
    # uvicorn treats `forwarded_allow_ips=None` as "read the env var, default
    # 127.0.0.1" and still trusts proxy headers from there — not "trust none".
    # Empty `FORWARDED_ALLOW_IPS` means trust no proxy, so disable the
    # middleware outright instead of passing it an empty/None IP list.
    uvicorn.run(
        "vieneu_portal.app:create_app",
        factory=True,
        host=settings.HOST,
        port=settings.PORT,
        proxy_headers=bool(settings.FORWARDED_ALLOW_IPS),
        forwarded_allow_ips=settings.FORWARDED_ALLOW_IPS or "127.0.0.1",
    )


def _worker() -> None:
    from .jobs.recording_render_worker_loop import main as worker_main

    worker_main()


def _alembic_config(sqlalchemy_url: str):
    from alembic.config import Config

    cfg = Config(str(PACKAGE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(PACKAGE_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", sqlalchemy_url)
    return cfg


def _db_upgrade(no_backup: bool) -> None:
    from alembic import command

    from .config import get_settings
    from .db.database_backup_before_migrate import backup_before_upgrade

    settings = get_settings()
    dump_path = backup_before_upgrade(
        settings.DATABASE_URL, Path(settings.BACKUP_DIR), skip_backup=no_backup
    )
    if dump_path:
        print(f"Backed up database to {dump_path}")
    command.upgrade(_alembic_config(settings.sqlalchemy_database_url), "head")


def _db_current() -> None:
    from alembic import command

    from .config import get_settings

    settings = get_settings()
    command.current(_alembic_config(settings.sqlalchemy_database_url), verbose=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
    from .admin_cli.cli_parser_and_dispatch import register_admin_cli_commands

    parser = argparse.ArgumentParser(prog="python -m vieneu_portal")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve")
    sub.add_parser("worker")

    db_parser = sub.add_parser("db")
    db_sub = db_parser.add_subparsers(dest="db_command", required=True)
    upgrade_parser = db_sub.add_parser("upgrade")
    upgrade_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="skip the pre-migration pg_dump (required when pg_dump is unavailable)",
    )
    db_sub.add_parser("current")

    register_admin_cli_commands(sub)

    args = parser.parse_args(argv)
    if args.command == "serve":
        _serve()
        return 0
    if args.command == "worker":
        _worker()
        return 0
    if args.command == "db":
        if args.db_command == "upgrade":
            _db_upgrade(no_backup=args.no_backup)
        elif args.db_command == "current":
            _db_current()
        return 0
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
