"""Pydantic models for tool parameters and responses."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PassengerFilters(BaseModel):
    """Human-readable filters for querying passengers."""

    survived: bool | None = Field(None, description="Filter by survival status")
    pclass: int | None = Field(None, ge=1, le=3, description="Passenger class (1, 2, or 3)")
    sex: Literal["male", "female"] | None = Field(None, description="Gender")
    age_min: float | None = Field(None, ge=0, description="Minimum age")
    age_max: float | None = Field(None, ge=0, description="Maximum age")
    embarked: Literal["C", "Q", "S"] | None = Field(None, description="Port of embarkation")
    who: Literal["child", "man", "woman"] | None = Field(None, description="Category: child, man, or woman")
    deck: Literal["A", "B", "C", "D", "E", "F", "G"] | None = Field(None, description="Deck letter")
    alone: bool | None = Field(None, description="Travelling alone")
    adult_male: bool | None = Field(None, description="Is adult male")
    embark_town: Literal["Cherbourg", "Queenstown", "Southampton"] | None = Field(
        None, description="Embarkation town"
    )

    def to_filter_dict(self) -> dict[str, Any]:
        """Convert to filter dict, excluding None values."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class QueryPassengersParams(BaseModel):
    """Parameters for the query_passengers tool."""

    filters: PassengerFilters | None = Field(None, description="Filters to apply")
    columns: list[str] | None = Field(
        None, description="Columns to return (all if not specified)"
    )
    limit: int = Field(50, ge=1, le=200, description="Maximum number of rows to return")
    offset: int = Field(0, ge=0, description="Number of rows to skip")


class AggregateParams(BaseModel):
    """Parameters for the aggregate_stats tool."""

    group_by: str = Field(..., description="Column to group by (e.g., 'sex', 'pclass', 'class')")
    metric: Literal["count", "avg", "sum", "min", "max"] = Field(
        ..., description="Aggregation function"
    )
    column: str = Field(..., description="Column to aggregate")
    filters: PassengerFilters | None = Field(None, description="Optional filters")


class SurvivalAnalysisParams(BaseModel):
    """Parameters for the get_survival_analysis tool."""

    dimension: Literal["class", "sex", "embarked", "age_group", "deck", "who", "alone"] = Field(
        ..., description="Dimension to analyze survival by"
    )
