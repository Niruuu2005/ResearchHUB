"""Pytest bootstrap: isolate tests from the developer SQLite DB and data/ folders.

This module runs before test collection imports `app`, so engine/settings bind to a temp tree.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="researchops_pytest_"))
(_TEST_ROOT / "documents").mkdir(parents=True, exist_ok=True)
(_TEST_ROOT / "exports").mkdir(parents=True, exist_ok=True)

_db_path = (_TEST_ROOT / "test.db").as_posix()
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["STORAGE_PATH"] = str(_TEST_ROOT / "documents")
os.environ["EXPORT_STORAGE_PATH"] = str(_TEST_ROOT / "exports")
os.environ.setdefault("LLM_PROVIDER", "heuristic")
os.environ.setdefault("EMBEDDING_PROVIDER", "heuristic")
os.environ["ALLOW_MOCK_AUTH"] = "true"
os.environ["SESSION_SECRET_KEY"] = "test-session-secret-key-32-bytes-long!!"

import pytest
from starlette.testclient import TestClient
from app.db.session import SessionLocal, init_db
from app.models.database import User
from app.services.auth_service import AuthService

_default_token = None


def get_or_create_default_test_token() -> str:
    global _default_token
    if _default_token:
        return _default_token
    init_db()
    with SessionLocal() as db:
        user = db.query(User).filter(User.google_sub == "test_sub_default_suite").first()
        if not user:
            user = User(
                id=str(uuid.uuid4()),
                google_sub="test_sub_default_suite",
                email="devops_tester@example.com",
                full_name="Default CI Tester",
                profile_picture="https://example.com/avatar.png",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        _default_token = AuthService.create_session_token(user)
        return _default_token


_orig_request = TestClient.request


def _patched_request(self, method, url, **kwargs):
    headers = kwargs.get("headers")
    if headers is None:
        headers = {}
    elif isinstance(headers, dict):
        headers = dict(headers)
    else:
        headers = dict(headers)

    if headers.get("X-Test-Anonymous") == "true":
        del headers["X-Test-Anonymous"]
    elif (
        "Authorization" not in headers
        and "authorization" not in headers
        and "Cookie" not in headers
        and "cookie" not in headers
    ):
        token = get_or_create_default_test_token()
        headers["Authorization"] = f"Bearer {token}"

    kwargs["headers"] = headers
    return _orig_request(self, method, url, **kwargs)


TestClient.request = _patched_request

