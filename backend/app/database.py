"""Database engine / session factory (SQLAlchemy 2.x).

Works unchanged against PostgreSQL, MySQL or SQLite – the dialect is chosen
by ``DATABASE_URL`` (see config.py / .env.example).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from . import config

connect_args = {}
if config.DATABASE_URL.startswith("sqlite"):
    # Needed because the LangGraph tools may run in a worker thread.
    connect_args["check_same_thread"] = False

engine = create_engine(config.DATABASE_URL, connect_args=connect_args, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency – yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
