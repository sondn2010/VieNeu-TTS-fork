"""`pg_dump` the target database before an Alembic upgrade, mirroring the
backup-before-migrate pattern in `src/vieneu_admin/db.py`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from ..config import to_libpq_url


def _without_password(libpq_url: str) -> tuple[str, Optional[str]]:
    """Split a libpq URL into a password-free URL plus the password, so the
    password never appears in a subprocess argv (visible via `ps`) or in a
    `CalledProcessError` traceback.
    """
    parts = urlsplit(libpq_url)
    if parts.password is None:
        return libpq_url, None
    userinfo = parts.username or ""
    netloc = f"{userinfo}@{parts.hostname or ''}"
    if parts.port:
        netloc += f":{parts.port}"
    sanitized = urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    return sanitized, parts.password


def _has_existing_tables(database_url: str) -> bool:
    import psycopg

    with psycopg.connect(to_libpq_url(database_url)) as conn:
        with conn.cursor() as cur:
            # pg_catalog (unlike information_schema.tables) lists tables
            # regardless of the connecting role's table-level grants.
            cur.execute("SELECT COUNT(*) FROM pg_catalog.pg_tables WHERE schemaname = 'public'")
            (count,) = cur.fetchone()
    return count > 0


def backup_before_upgrade(
    database_url: str, backup_dir: Path, *, skip_backup: bool = False
) -> Optional[Path]:
    """Dump the database to `backup_dir` before a migration runs.

    No-ops on an empty database or when `skip_backup` is set. Aborts (raises)
    when the database already has tables but `pg_dump` is not on PATH, instead
    of silently migrating without a backup.
    """
    if skip_backup:
        return None
    if not _has_existing_tables(database_url):
        return None
    if shutil.which("pg_dump") is None:
        raise RuntimeError(
            "pg_dump not found on PATH; install postgresql-client or pass --no-backup "
            "to upgrade without a pre-migration backup"
        )
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = backup_dir / f"portal-{stamp}.dump"

    sanitized_url, password = _without_password(to_libpq_url(database_url))
    env = dict(os.environ)
    if password:
        env["PGPASSWORD"] = password
    try:
        subprocess.run(["pg_dump", "-Fc", sanitized_url, "-f", str(dest)], check=True, env=env)
    except subprocess.CalledProcessError as exc:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"pg_dump failed with exit code {exc.returncode}") from None
    return dest
