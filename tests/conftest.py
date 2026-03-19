"""Shared test fixtures for MCP DataBridge tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from mcp_databridge import config as config_module


@pytest.fixture(autouse=True)
def _use_test_db(tmp_path: Path) -> None:
    """Copy the real database to a temp location for test isolation."""
    source_db = Path(__file__).parent.parent / "data" / "titanic.db"
    test_db = tmp_path / "titanic.db"
    shutil.copy2(source_db, test_db)

    # Patch settings to use the test database
    original_path = config_module.settings.db_path
    config_module.settings.db_path = test_db
    yield
    config_module.settings.db_path = original_path
