"""Tests for analytics tools: aggregate_stats, get_survival_analysis, describe_column."""

from __future__ import annotations

import json

import pytest

from mcp_databridge.database import aggregate, get_column_stats
from mcp_databridge.tools.analytics import get_survival_analysis


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

    def test_with_missing_filter(self) -> None:
        """Aggregate with deck='missing' should only include passengers with NULL deck."""
        results = aggregate("sex", "count", "survived", filters={"deck": "missing"})
        total = sum(r["count_survived"] for r in results)
        assert total == 688  # 688 passengers have missing deck


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
        assert stats["missing"] == 0
        assert stats["total"] == 891
        values = {d["value"] for d in stats["distribution"]}
        assert values == {"male", "female"}

    def test_class_column(self) -> None:
        stats = get_column_stats("class")
        assert stats["type"] == "categorical"
        assert stats["unique_values"] == 3
        assert stats["missing"] == 0
        values = {d["value"] for d in stats["distribution"]}
        assert values == {"First", "Second", "Third"}

    def test_deck_column_excludes_none_from_unique(self) -> None:
        """Deck has 7 real values (A-G) and 688 missing — unique_values should be 7."""
        stats = get_column_stats("deck")
        assert stats["type"] == "categorical"
        assert stats["unique_values"] == 7
        assert stats["missing"] == 688
        non_null_values = {d["value"] for d in stats["distribution"] if d["value"] is not None}
        assert non_null_values == {"A", "B", "C", "D", "E", "F", "G"}

    def test_embarked_column_excludes_none_from_unique(self) -> None:
        """Embarked has 3 real values (C/Q/S) and 2 missing — unique_values should be 3."""
        stats = get_column_stats("embarked")
        assert stats["type"] == "categorical"
        assert stats["unique_values"] == 3
        assert stats["missing"] == 2

    def test_fare_column(self) -> None:
        stats = get_column_stats("fare")
        assert stats["type"] == "numeric"
        assert stats["min"] >= 0
        assert stats["max"] > 0

    def test_invalid_column(self) -> None:
        with pytest.raises(ValueError, match="Unknown column"):
            get_column_stats("nonexistent")


class TestSurvivalAnalysis:
    def test_by_sex(self) -> None:
        result = json.loads(get_survival_analysis("sex"))
        assert result["dimension"] == "sex"
        sexes = {r["sex"] for r in result["results"]}
        assert sexes == {"male", "female"}
        # Women survived at higher rate than men
        female = next(r for r in result["results"] if r["sex"] == "female")
        male = next(r for r in result["results"] if r["sex"] == "male")
        assert female["survival_rate_pct"] > male["survival_rate_pct"]

    def test_by_class(self) -> None:
        result = json.loads(get_survival_analysis("class"))
        classes = {r["class"] for r in result["results"]}
        assert classes == {"First", "Second", "Third"}

    def test_by_age_group(self) -> None:
        result = json.loads(get_survival_analysis("age_group"))
        groups = {r["age_group"] for r in result["results"]}
        assert "Child (0-11)" in groups
        assert "Unknown" in groups  # 177 passengers with missing age

    def test_by_deck_includes_none(self) -> None:
        """Deck survival analysis should include a None group for 688 missing values."""
        result = json.loads(get_survival_analysis("deck"))
        decks = {r["deck"] for r in result["results"]}
        assert None in decks
        assert "A" in decks
        null_group = next(r for r in result["results"] if r["deck"] is None)
        assert null_group["total_count"] == 688

    def test_totals_add_up(self) -> None:
        result = json.loads(get_survival_analysis("sex"))
        total = sum(r["total_count"] for r in result["results"])
        assert total == 891

    def test_invalid_dimension(self) -> None:
        result = json.loads(get_survival_analysis("nonexistent"))
        assert "error" in result
