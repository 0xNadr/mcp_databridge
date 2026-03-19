"""Tests for query tools: query_passengers, get_passenger, list_tables."""

from __future__ import annotations

import pytest

from mcp_databridge.database import (
    get_passenger_by_rowid,
    get_table_schemas,
    query_resolved,
)


class TestQueryResolved:
    def test_returns_results(self) -> None:
        rows = query_resolved(limit=5)
        assert len(rows) == 5
        assert "sex" in rows[0]
        assert "class" in rows[0]

    def test_filter_by_sex(self) -> None:
        rows = query_resolved(filters={"sex": "female"}, limit=200)
        assert all(r["sex"] == "female" for r in rows)

    def test_filter_by_pclass(self) -> None:
        rows = query_resolved(filters={"pclass": 1}, limit=200)
        assert all(r["pclass"] == 1 for r in rows)

    def test_filter_combined(self) -> None:
        rows = query_resolved(filters={"sex": "female", "pclass": 1}, limit=200)
        assert all(r["sex"] == "female" and r["pclass"] == 1 for r in rows)

    def test_filter_age_range(self) -> None:
        rows = query_resolved(filters={"age_min": 20, "age_max": 30}, limit=200)
        assert all(20 <= r["age"] <= 30 for r in rows)

    def test_filter_boolean(self) -> None:
        rows = query_resolved(filters={"alone": True}, limit=200)
        assert all(r["alone"] == 1 for r in rows)

    def test_columns_selection(self) -> None:
        rows = query_resolved(columns=["sex", "age", "survived"], limit=5)
        assert set(rows[0].keys()) == {"sex", "age", "survived"}

    def test_invalid_filter_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown filter key"):
            query_resolved(filters={"nonexistent": "value"})

    def test_invalid_column_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown columns"):
            query_resolved(columns=["nonexistent"], limit=5)

    def test_limit_capped(self) -> None:
        rows = query_resolved(limit=1000)
        assert len(rows) <= 200  # max_results default

    def test_offset(self) -> None:
        all_rows = query_resolved(limit=10, offset=0)
        offset_rows = query_resolved(limit=5, offset=5)
        assert offset_rows[0] == all_rows[5]

    def test_resolved_labels(self) -> None:
        rows = query_resolved(limit=1)
        row = rows[0]
        assert row["sex"] in ("male", "female")
        assert row["class"] in ("First", "Second", "Third")
        assert row["who"] in ("child", "man", "woman")
        assert row["alive"] in ("yes", "no")

    def test_filter_missing_deck(self) -> None:
        """Filter deck='missing' returns passengers with NULL deck (688 expected)."""
        rows = query_resolved(filters={"deck": "missing"}, limit=200)
        assert all(r["deck"] is None for r in rows)
        # There are 688 total — we get 200 (max) but all should be None
        assert len(rows) == 200

    def test_filter_missing_embarked(self) -> None:
        """Filter embarked='missing' returns the 2 passengers with NULL embarked."""
        rows = query_resolved(filters={"embarked": "missing"}, limit=200)
        assert len(rows) == 2
        assert all(r["embarked"] is None for r in rows)
        assert all(r["embark_town"] is None for r in rows)

    def test_filter_missing_embark_town(self) -> None:
        """Filter embark_town='missing' returns passengers with NULL embark_town."""
        rows = query_resolved(filters={"embark_town": "missing"}, limit=200)
        assert len(rows) == 2
        assert all(r["embark_town"] is None for r in rows)

    def test_filter_missing_combined_with_other(self) -> None:
        """Missing filter works in combination with other filters."""
        rows = query_resolved(filters={"deck": "missing", "pclass": 3}, limit=200)
        assert all(r["deck"] is None for r in rows)
        assert all(r["pclass"] == 3 for r in rows)


class TestGetPassenger:
    def test_valid_row(self) -> None:
        p = get_passenger_by_rowid(1)
        assert p is not None
        assert p["row_number"] == 1
        assert "sex" in p

    def test_last_row(self) -> None:
        p = get_passenger_by_rowid(891)
        assert p is not None

    def test_invalid_row(self) -> None:
        p = get_passenger_by_rowid(9999)
        assert p is None

    def test_resolved_labels(self) -> None:
        p = get_passenger_by_rowid(2)
        assert p is not None
        assert p["sex"] == "female"
        assert p["class"] == "First"
        assert p["survived"] == 1


class TestListTables:
    def test_returns_all_tables(self) -> None:
        schemas = get_table_schemas()
        table_names = {s["table"] for s in schemas}
        assert "Observation" in table_names
        assert "Sex" in table_names
        assert "Class" in table_names
        assert len(schemas) == 8

    def test_observation_row_count(self) -> None:
        schemas = get_table_schemas()
        obs = next(s for s in schemas if s["table"] == "Observation")
        assert obs["row_count"] == 891

    def test_columns_present(self) -> None:
        schemas = get_table_schemas()
        obs = next(s for s in schemas if s["table"] == "Observation")
        col_names = {c["name"] for c in obs["columns"]}
        assert "survived" in col_names
        assert "age" in col_names
        assert "sex_id" in col_names
