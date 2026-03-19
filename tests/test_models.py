"""Tests for Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_databridge.models import (
    AggregateParams,
    PassengerFilters,
    QueryPassengersParams,
    SurvivalAnalysisParams,
)


class TestPassengerFilters:
    def test_empty_filters(self) -> None:
        f = PassengerFilters()
        assert f.to_filter_dict() == {}

    def test_single_filter(self) -> None:
        f = PassengerFilters(sex="female")
        assert f.to_filter_dict() == {"sex": "female"}

    def test_multiple_filters(self) -> None:
        f = PassengerFilters(sex="male", pclass=1, survived=True)
        d = f.to_filter_dict()
        assert d == {"sex": "male", "pclass": 1, "survived": True}

    def test_age_range(self) -> None:
        f = PassengerFilters(age_min=20, age_max=40)
        assert f.to_filter_dict() == {"age_min": 20, "age_max": 40}

    def test_invalid_pclass(self) -> None:
        with pytest.raises(ValidationError):
            PassengerFilters(pclass=5)

    def test_invalid_sex(self) -> None:
        with pytest.raises(ValidationError):
            PassengerFilters(sex="invalid")


class TestQueryPassengersParams:
    def test_defaults(self) -> None:
        p = QueryPassengersParams()
        assert p.limit == 50
        assert p.offset == 0
        assert p.filters is None
        assert p.columns is None

    def test_custom_values(self) -> None:
        p = QueryPassengersParams(limit=100, offset=10, columns=["age", "fare"])
        assert p.limit == 100
        assert p.offset == 10

    def test_limit_max(self) -> None:
        with pytest.raises(ValidationError):
            QueryPassengersParams(limit=300)


class TestAggregateParams:
    def test_valid(self) -> None:
        p = AggregateParams(group_by="sex", metric="avg", column="fare")
        assert p.group_by == "sex"
        assert p.metric == "avg"

    def test_invalid_metric(self) -> None:
        with pytest.raises(ValidationError):
            AggregateParams(group_by="sex", metric="invalid", column="fare")


class TestSurvivalAnalysisParams:
    def test_valid(self) -> None:
        p = SurvivalAnalysisParams(dimension="class")
        assert p.dimension == "class"

    def test_invalid_dimension(self) -> None:
        with pytest.raises(ValidationError):
            SurvivalAnalysisParams(dimension="invalid")
