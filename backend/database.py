"""
Database connection management.

Local development uses SQLite. Set the DATABASE_URL environment variable to
switch to PostgreSQL/Supabase in production without touching any other code.

Example production value:
    postgresql://USER:PASSWORD@HOST:5432/DBNAME
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Local dev convenience: load backend/.env if present. Real environment
# variables always win (load_dotenv never overrides them), which is what you
# want on Render/Railway/Supabase where config comes from the dashboard.
load_dotenv(Path(__file__).resolve().parent / ".env")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./prime_tracking.db")

# SQLite needs this flag to allow use across multiple threads (FastAPI's
# default threadpool). PostgreSQL/Supabase connections ignore it safely
# because we only pass it when the URL is sqlite.
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {"connect_args": {"check_same_thread": False}}
else:
    # Pool hardening for managed Postgres (Supabase/Render):
    # - pool_pre_ping: drop dead connections instead of raising
    #   "server closed the connection" after an idle period.
    # - pool_recycle: proactively rotate connections before the provider's
    #   idle timeout kills them.
    # - explicit pool sizing so a burst of requests queues instead of
    #   opening unbounded connections against the pooler.
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": int(os.environ.get("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "10")),
    }

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
