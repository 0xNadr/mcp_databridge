"""Analytics tools: aggregate_stats, get_survival_analysis, describe_column."""

from __future__ import annotations

import json
import time
from typing import Any

import structlog

from mcp_databridge.database import (
    RESOLVED_VIEW_SQL,
    aggregate,
    get_column_stats,
    get_connection,
)

logger = structlog.get_logger()


def aggregate_stats(
    group_by: str,
    metric: str,
    column: str,
    filters: dict[str, Any] | None = None,
) -> str:
    """Run aggregation queries on passenger data grouped by a dimension.

    Compute count, avg, sum, min, or max of any column, grouped by any dimension.

    Examples:
        - Average fare by class: group_by="class", metric="avg", column="fare"
        - Survival count by sex: group_by="sex", metric="sum", column="survived"
        - Max age by deck: group_by="deck", metric="max", column="age"

    Args:
        group_by: Column to group by (e.g., 'sex', 'pclass', 'class', 'who', 'deck').
        metric: Aggregation function — one of: count, avg, sum, min, max.
        column: Column to aggregate (e.g., 'survived', 'fare', 'age').
        filters: Optional filters (same syntax as query_passengers).
    """
    start = time.monotonic()
    try:
        results = aggregate(group_by=group_by, metric=metric, column=column, filters=filters)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "tool.aggregate_stats",
            group_by=group_by,
            metric=metric,
            column=column,
            row_count=len(results),
            duration_ms=round(duration_ms, 2),
        )
        return json.dumps({"results": results, "count": len(results)}, default=str)
    except ValueError as e:
        logger.warning("tool.aggregate_stats.error", error=str(e))
        return json.dumps({"error": str(e)})


def get_survival_analysis(dimension: str) -> str:
    """Analyze survival rates across a specific dimension.

    Returns survival count, total count, and survival rate for each value
    of the specified dimension.

    Examples:
        - dimension="sex" → 74.2% female vs 18.9% male survival
        - dimension="class" → First: 63%, Second: 47%, Third: 24%
        - dimension="age_group" → Child, Teenager, Young Adult, etc.

    Args:
        dimension: One of: class, sex, embarked, age_group, deck, who, alone.
    """
    start = time.monotonic()
    valid_dimensions = {
        "class",
        "sex",
        "embarked",
        "age_group",
        "deck",
        "who",
        "alone",
    }
    if dimension not in valid_dimensions:
        valid = sorted(valid_dimensions)
        return json.dumps({"error": f"Invalid dimension: {dimension!r}. Valid: {valid}"})

    try:
        resolved_cte = f"WITH resolved AS ({RESOLVED_VIEW_SQL})"

        if dimension == "age_group":
            sql = f"""
                {resolved_cte}
                SELECT
                    CASE
                        WHEN age IS NULL THEN 'Unknown'
                        WHEN age < 12 THEN 'Child (0-11)'
                        WHEN age < 18 THEN 'Teenager (12-17)'
                        WHEN age < 35 THEN 'Young Adult (18-34)'
                        WHEN age < 55 THEN 'Middle Aged (35-54)'
                        ELSE 'Senior (55+)'
                    END as {dimension},
                    SUM(survived) as survived_count,
                    COUNT(*) as total_count,
                    ROUND(AVG(survived) * 100, 2) as survival_rate_pct
                FROM resolved
                GROUP BY 1
                ORDER BY survival_rate_pct DESC
            """
        else:
            sql = f"""
                {resolved_cte}
                SELECT
                    {dimension},
                    SUM(survived) as survived_count,
                    COUNT(*) as total_count,
                    ROUND(AVG(survived) * 100, 2) as survival_rate_pct
                FROM resolved
                GROUP BY {dimension}
                ORDER BY survival_rate_pct DESC
            """

        with get_connection() as conn:
            cursor = conn.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "tool.get_survival_analysis",
            dimension=dimension,
            row_count=len(rows),
            duration_ms=round(duration_ms, 2),
        )
        return json.dumps({"dimension": dimension, "results": rows}, default=str)
    except Exception as e:
        logger.error("tool.get_survival_analysis.error", error=str(e))
        return json.dumps({"error": str(e)})


def describe_column(column: str) -> str:
    """Get a statistical summary for a column in the Titanic dataset.

    For numeric columns: count, missing, min, max, mean, median, sum.
    For categorical columns: total, missing, unique values, value distribution.

    Examples:
        - column="age" → count=714, missing=177, mean=29.7, median=28.0
        - column="fare" → min=0, max=512.33, mean=32.2
        - column="sex" → male: 577, female: 314

    Args:
        column: Column name (e.g., 'age', 'fare', 'sex', 'class', 'deck').
    """
    start = time.monotonic()
    try:
        stats = get_column_stats(column)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "tool.describe_column",
            column=column,
            duration_ms=round(duration_ms, 2),
        )
        return json.dumps(stats, default=str)
    except ValueError as e:
        logger.warning("tool.describe_column.error", error=str(e))
        return json.dumps({"error": str(e)})
