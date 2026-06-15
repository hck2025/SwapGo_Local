from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_connect_args = {"check_same_thread": False} if _settings.DATABASE_URL.startswith("sqlite") else {}

engine: Engine = create_engine(_settings.DATABASE_URL, connect_args=_connect_args, future=True)


@event.listens_for(engine, "connect")
def _enable_sqlite_wal(dbapi_connection, _):
    if _settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_schema() -> None:
    """Phase A에서는 alembic 대신 create_all로 시작. (PG 마이그레이션 시 alembic 도입)"""
    from app.db import models  # noqa: F401  - 모델 임포트로 메타데이터 등록

    Base.metadata.create_all(bind=engine)
