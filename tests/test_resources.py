"""Tests for MCP resources: info, sample, column stats."""

from __future__ import annotations

import json

from mcp_databridge.server import column_stats, dataset_info, dataset_sample


class TestDatasetInfo:
    def test_returns_valid_json(self) -> None:
        result = json.loads(dataset_info())
        assert "name" in result
        assert "tables" in result
        assert "missing_values" in result
        assert "relationships" in result

    def test_table_count(self) -> None:
        result = json.loads(dataset_info())
        assert len(result["tables"]) == 8

    def test_missing_values(self) -> None:
        result = json.loads(dataset_info())
        mv = result["missing_values"]
        assert mv["total_rows"] == 891
        assert mv["missing_age"] == 177
        assert mv["missing_deck"] == 688


class TestDatasetSample:
    def test_returns_5_rows(self) -> None:
        result = json.loads(dataset_sample())
        assert len(result) == 5

    def test_rows_have_resolved_labels(self) -> None:
        result = json.loads(dataset_sample())
        row = result[0]
        assert "sex" in row
        assert "class" in row
        assert row["sex"] in ("male", "female")


class TestColumnStats:
    def test_numeric_column(self) -> None:
        result = json.loads(column_stats("age"))
        assert result["type"] == "numeric"
        assert "mean" in result

    def test_categorical_column(self) -> None:
        result = json.loads(column_stats("sex"))
        assert result["type"] == "categorical"
        assert "distribution" in result

    def test_invalid_column(self) -> None:
        result = json.loads(column_stats("nonexistent"))
        assert "error" in result
