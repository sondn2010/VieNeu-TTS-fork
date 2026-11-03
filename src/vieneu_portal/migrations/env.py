from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from vieneu_portal.config import to_sqlalchemy_url
from vieneu_portal.db import Base

config = context.config

# `set_main_option("sqlalchemy.url", ...)` (used by `__main__.py` and the test
# harness) is what actually reaches here, not `config.attributes`.
db_url = config.get_main_option("sqlalchemy.url") or os.environ.get("VIENEU_PORTAL_DATABASE_URL")
if not db_url:
    raise RuntimeError(
        "VIENEU_PORTAL_DATABASE_URL (or Config.set_main_option('sqlalchemy.url', ...)) "
        "is required to run migrations"
    )
config.set_main_option("sqlalchemy.url", to_sqlalchemy_url(db_url))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
