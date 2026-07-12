"""SQLAlchemy engine + session. SQLite for dev, Postgres-ready."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# check_same_thread only matters for SQLite; harmless to compute conditionally
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_session():
    """FastAPI-style dependency / context helper."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Import models first so they register on Base."""
    from app.db import models  # noqa: F401
    from app.auth import models as _auth_models  # noqa: F401  (registers users table)
    Base.metadata.create_all(bind=engine)
    _ensure_user_profile_columns()


def _ensure_user_profile_columns():
    """Lightweight migration: add profile columns to an existing users table.

    create_all() only creates missing TABLES — it never alters existing ones.
    This adds any missing profile columns so older databases upgrade in place.
    Idempotent and dialect-neutral (works on SQLite and Postgres).
    """
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    have = {c["name"] for c in insp.get_columns("users")}
    wanted = {
        "phone": "VARCHAR(20)",
        "institution": "VARCHAR(255)",
        "linkedin": "VARCHAR(500)",
        "orcid": "VARCHAR(100)",
        "website": "VARCHAR(500)",
        "research_interests": "VARCHAR(1000)",
    }
    missing = {k: v for k, v in wanted.items() if k not in have}
    if not missing:
        return
    with engine.begin() as conn:
        for col, coltype in missing.items():
            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {coltype}"))
