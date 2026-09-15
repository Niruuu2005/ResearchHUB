"""Pytest bootstrap: isolate tests from the developer SQLite DB and data/ folders.

This module runs before test collection imports `app`, so engine/settings bind to a temp tree.
"""
from __future__ import annotations

import os
import tempfile
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
