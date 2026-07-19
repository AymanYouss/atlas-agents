"""Alembic environment.

Reads the database URL from Atlas settings and runs migrations against the app's
SQLAlchemy metadata. The LangGraph checkpointer manages its own tables via
``AsyncPostgresSaver.setup()``; these migrations cover only the application
tables (``runs`` and ``run_events``).
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from atlas.config import get_settings
from atlas.persistence.db import Base
from atlas.persistence import sql as _sql  # noqa: F401 - registers models on Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    # Alembic uses a synchronous driver; strip the async prefix.
    return get_settings().database_url.replace("+asyncpg", "")


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
