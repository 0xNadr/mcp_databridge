"""Tests for analytics tools: aggregate_stats, get_survival_analysis, describe_column."""

from __future__ import annotations

import pytest

from mcp_databridge.database import aggregate, get_column_stats


class TestAggregate:
    def test_count_by_sex(self) -> None:
        results = aggregate("sex", "count", "survived")
        assert len(results) == 2
        sexes = {r["sex"] for r in results}
        assert sexes == {"male", "female"}

    def test_avg_fare_by_class(self) -> None:
        results = aggregate("class", "avg", "fare")
        assert len(results) == 3
        classes = {r["class"] for r in results}
        assert classes == {"First", "Second", "Third"}
        # First class should have highest average fare
        first = next(r for r in results if r["class"] == "First")
        third = next(r for r in results if r["class"] == "Third")
        assert first["avg_fare"] > third["avg_fare"]

    def test_sum_survived_by_who(self) -> None:
        results = aggregate("who", "sum", "survived")
        assert len(results) == 3

    def test_with_filters(self) -> None:
        results = aggregate("sex", "count", "survived", filters={"pclass": 1})
        total = sum(r["count_survived"] for r in results)
        assert total < 891  # Should be less than full dataset

    def test_invalid_metric(self) -> None:
        with pytest.raises(ValueError, match="Invalid metric"):
            aggregate("sex", "invalid", "survived")

    def test_invalid_group_by(self) -> None:
        with pytest.raises(ValueError, match="Unknown group_by"):
            aggregate("nonexistent", "count", "survived")


class TestColumnStats:
    def test_numeric_column(self) -> None:
        stats = get_column_stats("age")
        assert stats["type"] == "numeric"
        assert stats["count"] == 714
        assert stats["missing"] == 177
        assert stats["min"] == 0.42
        assert stats["max"] == 80.0
        assert stats["median"] is not None

    def test_categorical_column(self) -> None:
        stats = get_column_stats("sex")
        assert stats["type"] == "categorical"
        assert stats["unique_values"] == 2
        assert stats["total"] == 891
        values = {d["value"] for d in stats["distribution"]}
        assert values == {"male", "female"}

    def test_class_column(self) -> None:
        stats = get_column_stats("class")
        assert stats["type"] == "categorical"
        assert stats["unique_values"] == 3
        values = {d["value"] for d in stats["distribution"]}
        assert values == {"First", "Second", "Third"}

    def test_fare_column(self) -> None:
        stats = get_column_stats("fare")
        assert stats["type"] == "numeric"
        assert stats["min"] >= 0
        assert stats["max"] > 0

    def test_invalid_column(self) -> None:
        with pytest.raises(ValueError, match="Unknown column"):
            get_column_stats("nonexistent")
