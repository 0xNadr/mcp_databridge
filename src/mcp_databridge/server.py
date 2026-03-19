"""MCP DataBridge server — FastMCP server definition with tools, resources, and prompts."""

from __future__ import annotations

import json
import time
from typing import Any

import structlog
from mcp.server.fastmcp import FastMCP

from mcp_databridge.config import settings
from mcp_databridge.database import (
    aggregate,
    execute_readonly_sql,
    get_column_stats,
    get_passenger_by_rowid,
    get_table_schemas,
    query_resolved,
)
from mcp_databridge.logging import setup_logging

setup_logging()
logger = structlog.get_logger()

mcp = FastMCP(
    "MCP DataBridge",
    instructions=(
        "MCP DataBridge provides access to the Titanic passenger dataset. "
        "Use the tools to query, filter, aggregate, and analyze passenger data. "
        "All data is returned with human-readable labels (e.g., 'female' not '0'). "
        "Start with list_tables or query_passengers to explore the data."
    ),
)


# --- Tools ---


@mcp.tool()
def query_passengers(
    filters: dict[str, Any] | None = None,
    columns: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Query and filter Titanic passengers with human-readable results.

    Filter passengers using intuitive labels like sex='female', pclass=1, embarked='S'.
    Returns fully resolved data with all lookup values joined.

    Available filter keys: survived (bool), pclass (1-3), sex (male/female),
    age_min, age_max, embarked (C/Q/S), who (child/man/woman), deck (A-G),
    alone (bool), adult_male (bool), embark_town (Cherbourg/Queenstown/Southampton).

    Args:
        filters: Optional dict of filters (e.g., {"sex": "female", "pclass": 1}).
        columns: Optional list of columns to return. Returns all if not specified.
        limit: Max rows to return (1-200, default 50).
        offset: Number of rows to skip for pagination.
    """
    start = time.monotonic()
    try:
        results = query_resolved(filters=filters, columns=columns, limit=limit, offset=offset)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "tool.query_passengers",
            row_count=len(results),
            filters=filters,
            duration_ms=round(duration_ms, 2),
        )
        return json.dumps({"rows": results, "count": len(results)}, default=str)
    except ValueError as e:
        logger.warning("tool.query_passengers.error", error=str(e))
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_passenger(row_number: int) -> str:
    """Get a single passenger by their row number (1-based).

    Returns all fields with resolved labels for the specified passenger.

    Args:
        row_number: The 1-based row number of the passenger (1-891).
    """
    start = time.monotonic()
    if row_number < 1 or row_number > 891:
        return json.dumps({"error": "row_number must be between 1 and 891"})

    result = get_passenger_by_rowid(row_number)
    duration_ms = (time.monotonic() - start) * 1000
    if result is None:
        logger.warning("tool.get_passenger.not_found", row_number=row_number)
        return json.dumps({"error": f"No passenger found at row {row_number}"})

    logger.info("tool.get_passenger", row_number=row_number, duration_ms=round(duration_ms, 2))
    return json.dumps(result, default=str)


@mcp.tool()
def list_tables() -> str:
    """List all tables in the Titanic database with their schemas and row counts.

    Returns table names, column definitions (name, type, nullable), and row counts.
    Useful for understanding the normalized database structure.
    """
    start = time.monotonic()
    schemas = get_table_schemas()
    duration_ms = (time.monotonic() - start) * 1000
    logger.info("tool.list_tables", table_count=len(schemas), duration_ms=round(duration_ms, 2))
    return json.dumps(schemas, default=str)


@mcp.tool()
def aggregate_stats(
    group_by: str,
    metric: str,
    column: str,
    filters: dict[str, Any] | None = None,
) -> str:
    """Run aggregation queries on passenger data grouped by a dimension.

    Compute count, avg, sum, min, or max of any column, grouped by any dimension.

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


@mcp.tool()
def get_survival_analysis(dimension: str) -> str:
    """Analyze survival rates across a specific dimension.

    Returns survival count, total count, and survival rate for each value
    of the specified dimension.

    Args:
        dimension: One of: class, sex, embarked, age_group, deck, who, alone.
    """
    start = time.monotonic()
    valid_dimensions = {"class", "sex", "embarked", "age_group", "deck", "who", "alone"}
    if dimension not in valid_dimensions:
        valid = sorted(valid_dimensions)
        return json.dumps({"error": f"Invalid dimension: {dimension!r}. Valid: {valid}"})

    try:
        from mcp_databridge.database import (  # noqa: I001
            RESOLVED_VIEW_SQL,
            get_connection,
        )

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


@mcp.tool()
def describe_column(column: str) -> str:
    """Get a statistical summary for a column in the Titanic dataset.

    For numeric columns: count, missing, min, max, mean, median, sum.
    For categorical columns: total, missing, unique values, value distribution.

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


@mcp.tool()
def run_sql(query: str) -> str:
    """Execute a read-only SQL query against the Titanic database.

    Only SELECT statements are allowed. Results are limited to 200 rows.
    Use this for custom queries that aren't covered by other tools.

    The database has these tables: Observation (main), Sex, Embarked, Class,
    Who, Deck, EmbarkTown, Alive (all lookup tables with _id foreign keys).

    Args:
        query: A SELECT SQL query to execute.
    """
    start = time.monotonic()
    try:
        results = execute_readonly_sql(query)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "tool.run_sql",
            row_count=len(results),
            duration_ms=round(duration_ms, 2),
        )
        return json.dumps({"rows": results, "count": len(results)}, default=str)
    except ValueError as e:
        logger.warning("tool.run_sql.error", error=str(e), query=query)
        return json.dumps({"error": str(e)})


# --- Resources ---


@mcp.resource("databridge://info")
def dataset_info() -> str:
    """Titanic dataset overview: schema, relationships, row counts, missing values."""
    schemas = get_table_schemas()

    from mcp_databridge.database import get_connection

    with get_connection() as conn:
        # Missing value summary for Observation
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total_rows,
                SUM(CASE WHEN age IS NULL THEN 1 ELSE 0 END) as missing_age,
                SUM(CASE WHEN deck_id = -1 THEN 1 ELSE 0 END) as missing_deck,
                SUM(CASE WHEN embarked_id = -1 THEN 1 ELSE 0 END) as missing_embarked
            FROM Observation
        """)
        missing = dict(cursor.fetchone())

    info = {
        "name": "Titanic Passenger Dataset",
        "description": (
            "Historical data on 891 passengers aboard the RMS Titanic. "
            "The database is normalized with a main Observation table and "
            "7 lookup tables for categorical values."
        ),
        "tables": schemas,
        "missing_values": missing,
        "relationships": {
            "Observation.sex_id": "Sex.sex_id",
            "Observation.embarked_id": "Embarked.embarked_id",
            "Observation.class_id": "Class.class_id",
            "Observation.who_id": "Who.who_id",
            "Observation.deck_id": "Deck.deck_id",
            "Observation.embark_town_id": "EmbarkTown.embark_town_id",
            "Observation.alive_id": "Alive.alive_id",
        },
        "notes": [
            "Missing categorical values are encoded as -1 foreign keys, not NULL",
            "The 'survived' (int) and 'alive' (text) columns are redundant",
            "Use the tools (query_passengers, aggregate_stats) for resolved human-readable data",
        ],
    }
    return json.dumps(info, indent=2, default=str)


@mcp.resource("databridge://sample")
def dataset_sample() -> str:
    """First 5 passengers with all labels resolved — a quick preview of the data."""
    rows = query_resolved(limit=5)
    return json.dumps(rows, indent=2, default=str)


@mcp.resource("databridge://stats/{column}")
def column_stats(column: str) -> str:
    """Statistical summary for a specific column in the dataset."""
    try:
        stats = get_column_stats(column)
        return json.dumps(stats, indent=2, default=str)
    except ValueError as e:
        return json.dumps({"error": str(e)})


# --- Prompts ---


@mcp.prompt()
def explore_dataset() -> str:
    """Guide an AI agent through exploring the Titanic dataset step by step."""
    return (
        "You are exploring the Titanic passenger dataset through MCP DataBridge.\n\n"
        "Start by understanding the data:\n"
        "1. Use `list_tables` to see the database schema (8 normalized tables)\n"
        "2. Read the `databridge://info` resource for an overview\n"
        "3. Read `databridge://sample` to see example rows\n\n"
        "Then explore:\n"
        "4. Use `describe_column` on key columns: age, fare, sex, class, deck\n"
        "5. Use `query_passengers` with filters to find specific groups\n"
        "6. Use `aggregate_stats` to compute averages, counts, etc.\n"
        "7. Use `get_survival_analysis` to analyze survival by class, sex, age_group, etc.\n\n"
        "Key facts about this dataset:\n"
        "- 891 passengers, ~38% survived\n"
        "- 20% of age values are missing\n"
        "- 77% of deck values are missing\n"
        "- The database is normalized: use the tools for human-readable results\n"
    )


@mcp.prompt()
def survival_analysis() -> str:
    """Step-by-step survival analysis workflow for the Titanic dataset."""
    return (
        "Perform a comprehensive survival analysis of the Titanic dataset:\n\n"
        "1. **Overall survival rate**: Use `aggregate_stats` with group_by='survived', "
        "metric='count', column='survived'\n\n"
        "2. **By class**: Use `get_survival_analysis` with dimension='class'\n"
        "   - First class had the highest survival rate\n\n"
        "3. **By gender**: Use `get_survival_analysis` with dimension='sex'\n"
        "   - 'Women and children first' policy is clearly visible\n\n"
        "4. **By age group**: Use `get_survival_analysis` with dimension='age_group'\n"
        "   - Children had a notably higher survival rate\n\n"
        "5. **Intersectional analysis**: Use `aggregate_stats` with filters\n"
        "   - Compare survival of 1st class women vs 3rd class men\n"
        '   - Use filters like {"sex": "female", "pclass": 1}\n\n'
        "6. **Fare analysis**: Use `aggregate_stats` to compare average fare "
        "of survivors vs non-survivors\n\n"
        "7. **Family size impact**: Analyze sibsp and parch columns\n"
    )


@mcp.prompt()
def data_quality_report() -> str:
    """Analyze data quality issues in the Titanic dataset."""
    return (
        "Generate a data quality report for the Titanic dataset:\n\n"
        "1. **Missing values**: Use `describe_column` for each column to identify gaps\n"
        "   - age: ~20% missing (177 of 891)\n"
        "   - deck: ~77% missing (688 of 891)\n"
        "   - embarked: 2 missing\n\n"
        "2. **Distributions**: Check each column's distribution\n"
        "   - Use `describe_column` on 'fare' — look for outliers\n"
        "   - Use `describe_column` on 'age' — check for reasonable range\n\n"
        "3. **Redundancy**: Note that 'survived' and 'alive' carry the same info\n\n"
        "4. **Encoding**: Missing categorical values use -1 foreign keys, not NULL\n"
        "   - This affects Deck, Embarked, and EmbarkTown\n\n"
        "5. **Summary**: Compile findings into a quality score and recommendations\n"
    )


def main() -> None:
    """Run the MCP DataBridge server."""
    logger.info(
        "server.starting",
        transport=settings.transport,
        db_path=str(settings.db_path),
    )
    mcp.run(transport=settings.transport)
