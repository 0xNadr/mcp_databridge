"""Tests for run_sql tool — security and correctness."""

from __future__ import annotations

import pytest

from mcp_databridge.database import execute_readonly_sql


class TestReadonlySQL:
    def test_simple_select(self) -> None:
        rows = execute_readonly_sql("SELECT COUNT(*) as cnt FROM Observation")
        assert rows[0]["cnt"] == 891

    def test_select_with_where(self) -> None:
        rows = execute_readonly_sql("SELECT * FROM Sex WHERE sex = 'female'")
        assert len(rows) == 1
        assert rows[0]["sex"] == "female"

    def test_select_with_join(self) -> None:
        rows = execute_readonly_sql(
            "SELECT o.survived, s.sex FROM Observation o "
            "JOIN Sex s ON o.sex_id = s.sex_id LIMIT 5"
        )
        assert len(rows) == 5
        assert "sex" in rows[0]

    def test_result_limited(self) -> None:
        rows = execute_readonly_sql("SELECT * FROM Observation")
        assert len(rows) <= 200


class TestSQLSecurity:
    def test_reject_insert(self) -> None:
        with pytest.raises(ValueError, match="Only SELECT"):
            execute_readonly_sql("INSERT INTO Sex VALUES (99, 'other')")

    def test_reject_update(self) -> None:
        with pytest.raises(ValueError, match="Only SELECT"):
            execute_readonly_sql("UPDATE Observation SET survived = 1")

    def test_reject_delete(self) -> None:
        with pytest.raises(ValueError, match="Only SELECT"):
            execute_readonly_sql("DELETE FROM Observation")

    def test_reject_drop(self) -> None:
        with pytest.raises(ValueError, match="Only SELECT"):
            execute_readonly_sql("DROP TABLE Observation")

    def test_reject_alter(self) -> None:
        with pytest.raises(ValueError, match="Only SELECT"):
            execute_readonly_sql("ALTER TABLE Observation ADD COLUMN foo TEXT")

    def test_reject_create(self) -> None:
        with pytest.raises(ValueError, match="Only SELECT"):
            execute_readonly_sql("CREATE TABLE evil (id INTEGER)")

    def test_reject_multiple_statements(self) -> None:
        with pytest.raises(ValueError, match="Multiple SQL statements"):
            execute_readonly_sql("SELECT 1; DROP TABLE Observation")

    def test_reject_attach(self) -> None:
        with pytest.raises(ValueError, match="Only SELECT"):
            execute_readonly_sql("ATTACH DATABASE ':memory:' AS evil")

    def test_reject_pragma(self) -> None:
        with pytest.raises(ValueError, match="Only SELECT"):
            execute_readonly_sql("PRAGMA table_info(Observation)")

    def test_invalid_sql(self) -> None:
        with pytest.raises(ValueError, match="SQL execution error"):
            execute_readonly_sql("SELECT * FROM nonexistent_table")
