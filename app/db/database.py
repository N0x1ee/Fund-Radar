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
