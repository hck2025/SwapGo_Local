"""테스트 공통 픽스처: 인메모리 SQLite + 시드된 풀/글로서리."""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# 테스트는 격리된 SQLite 파일 DB를 사용한다 (sqlite memory는 워커 분리 시 별도 연결됨)
_tmp = tempfile.NamedTemporaryFile(prefix="swapgo_test_", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ADMIN_BOOTSTRAP_TOKEN"] = "test-admin"


@pytest.fixture(scope="session", autouse=True)
def _init_schema():
    from app.db.base import init_schema

    init_schema()
    yield
    try:
        os.unlink(_tmp.name)
    except OSError:
        pass


@pytest.fixture()
def db():
    from app.db.base import SessionLocal

    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def seeded_db(db):
    from app.seeders import seed_glossary, seed_pools

    seed_pools.run(db)
    seed_glossary.run(db)
    return db


@pytest.fixture()
def client():
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c
