"""Alembic environment for Prime Crest Logistics.

Reads DATABASE_URL from the environment (same fallback as database.py) and
targets the SQLAlchemy metadata declared in models.py, so autogenerate
(`alembic revision --autogenerate -m "..."`) works out of the box.

SQLite migrations run in batch mode so future ALTERs work on SQLite too.
"""
import os
import sys
from pathlib import Path

# Make backend/ importable so `database` and `models` resolve no matter
# which directory alembic was invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import context  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from database import DATABASE_URL, Base  # noqa: E402
import models  # noqa: F401,E402  — importing registers all tables on Base.metadata

target_metadata = Base.metadata

IS_SQLITE = DATABASE_URL.startswith("sqlite")


def run_migrations_offline() -> None:
    """Configure context in --sql (offline) mode: emit SQL to stdout."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=IS_SQLITE,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Configure context with a live connection and run migrations."""
    connect_args = {"check_same_thread": False} if IS_SQLITE else {}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=IS_SQLITE,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
