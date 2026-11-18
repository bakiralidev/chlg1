import os
import sys
from pathlib import Path

# Prefer backend/venv site-packages (e.g. bcrypt<4.0.0 compatible with passlib)
BACKEND_DIR = Path(__file__).resolve().parents[1]
VENV_SITE = BACKEND_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Mock optional heavy/external modules if not installed in test environment
for _opt_mod in (
    "openpyxl",
    "docker",
    "apscheduler",
    "apscheduler.schedulers",
    "apscheduler.schedulers.asyncio",
):
    if _opt_mod not in sys.modules:
        try:
            __import__(_opt_mod)
        except ImportError:
            from unittest.mock import MagicMock
            sys.modules[_opt_mod] = MagicMock()

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_for_pytest_only")

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


from app.db.database import Base  # noqa: E402
from app.core import security as _sec  # noqa: E402
from app.services import auth_service as _auth_svc  # noqa: E402

# Speed up bcrypt in unit tests (4 rounds instead of 12)
_sec.pwd_context.update(bcrypt__rounds=4)
_auth_svc.pwd_context.update(bcrypt__rounds=4)


def run_coro(coro):
    """Drive an async coroutine without creating an OS socketpair event loop."""
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


class _SyncAsAsyncSession:
    """Lightweight AsyncSession adapter over stdlib sqlite3 for fast, hang-free tests."""

    def __init__(self, sync_session):
        self._s = sync_session

    def add(self, obj):
        return self._s.add(obj)

    def get_bind(self):
        return self._s.get_bind()

    async def execute(self, *args, **kwargs):
        return self._s.execute(*args, **kwargs)

    async def flush(self):
        return self._s.flush()

    async def commit(self):
        return self._s.commit()

    async def rollback(self):
        return self._s.rollback()

    async def refresh(self, obj):
        return self._s.refresh(obj)

    async def delete(self, obj):
        return self._s.delete(obj)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    sync_sess = SessionLocal()
    try:
        yield _SyncAsAsyncSession(sync_sess)
    finally:
        sync_sess.close()
        engine.dispose()
