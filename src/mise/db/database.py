"""SQLAlchemy engine, session factory, and initialization."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from mise.config import DATABASE_URL

# Ensure the data directory exists for SQLite
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

# SQLite needs check_same_thread=False for multi-threaded use
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """Yield a database session. Use as a context manager or dependency."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db():
    """Create all tables in the database."""
    # Import all models so they register with Base.metadata
    import mise.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)