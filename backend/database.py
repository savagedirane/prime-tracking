"""
Database connection management.

Local development uses SQLite. Set the DATABASE_URL environment variable to
switch to PostgreSQL/Supabase in production without touching any other code.

Example production value:
    postgresql://USER:PASSWORD@HOST:5432/DBNAME
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./prime_tracking.db")

# SQLite needs this flag to allow use across multiple threads (FastAPI's
# default threadpool). PostgreSQL/Supabase connections ignore it safely
# because we only pass it when the URL is sqlite.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
