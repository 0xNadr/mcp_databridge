"""Tests for the database layer: connections, schema, resolved view."""

from __future__ import annotations

from mcp_databridge.database import (
    get_connection,
    get_passenger_by_rowid,
    get_table_schemas,
    query_resolved,
)


class TestConnection:
    def test_connection_opens(self) -> None:
        with get_connection() as conn:
            cursor = conn.execute("SELECT 1 as test")
            assert cursor.fetchone()["test"] == 1

    def test_wal_mode_enabled(self) -> None:
        with get_connection() as conn:
            cursor = conn.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]
            assert mode == "wal"

    def test_row_factory_returns_dicts(self) -> None:
        with get_connection() as conn:
            cursor = conn.execute("SELECT 1 as val, 'test' as name")
            row = cursor.fetchone()
            assert row["val"] == 1
            assert row["name"] == "test"


class TestSchema:
    def test_all_tables_present(self) -> None:
        expected = {
            "Alive",
            "Class",
            "Deck",
            "EmbarkTown",
            "Embarked",
            "Observation",
            "Sex",
            "Who",
        }
        schemas = get_table_schemas()
        actual = {s["table"] for s in schemas}
        assert actual == expected

    def test_observation_has_all_columns(self) -> None:
        schemas = get_table_schemas()
        obs = next(s for s in schemas if s["table"] == "Observation")
        col_names = {c["name"] for c in obs["columns"]}
        expected = {
            "survived",
            "pclass",
            "age",
            "sibsp",
            "parch",
            "fare",
            "adult_male",
            "alone",
            "sex_id",
            "embarked_id",
            "class_id",
            "who_id",
            "deck_id",
            "embark_town_id",
            "alive_id",
        }
        assert expected.issubset(col_names)

    def test_lookup_table_row_counts(self) -> None:
        schemas = get_table_schemas()
        counts = {s["table"]: s["row_count"] for s in schemas}
        assert counts["Sex"] == 2
        assert counts["Class"] == 3
        assert counts["Who"] == 3
        assert counts["Alive"] == 2


class TestResolvedView:
    def test_joins_resolve_all_labels(self) -> None:
        rows = query_resolved(limit=1)
        row = rows[0]
        # All FK fields should be resolved to human-readable labels
        assert isinstance(row["sex"], str)
        assert isinstance(row["class"], str)
        assert isinstance(row["who"], str)
        assert isinstance(row["alive"], str)
        # Raw FK IDs should NOT be present
        assert "sex_id" not in row
        assert "class_id" not in row

    def test_row_number_is_sequential(self) -> None:
        rows = query_resolved(limit=5)
        row_numbers = [r["row_number"] for r in rows]
        assert row_numbers == [1, 2, 3, 4, 5]

    def test_total_dataset_size(self) -> None:
        rows = query_resolved(limit=200, offset=0)
        rows2 = query_resolved(limit=200, offset=200)
        rows3 = query_resolved(limit=200, offset=400)
        rows4 = query_resolved(limit=200, offset=600)
        rows5 = query_resolved(limit=200, offset=800)
        total = len(rows) + len(rows2) + len(rows3) + len(rows4) + len(rows5)
        assert total == 891

    def test_missing_deck_is_none(self) -> None:
        """Deck is missing for ~77% of passengers — should show as None/empty."""
        p = get_passenger_by_rowid(1)
        assert p is not None
        # Row 1 has deck_id = -1, which should resolve to None or empty
        assert p["deck"] is None or p["deck"] == ""
