"""Query tools: query_passengers, get_passenger, list_tables."""

from __future__ import annotations

import json
import time
from typing import Any

import structlog

from mcp_databridge.database import (
    get_passenger_by_rowid,
    get_table_schemas,
    query_resolved,
)

logger = structlog.get_logger()


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

    Examples:
        - First-class women: filters={"sex": "female", "pclass": 1}, limit=3
        - Survivors under 18: filters={"survived": true, "age_max": 18}
        - Error handling test: filters={"bad_column": "x"} → returns valid filter list

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


def get_passenger(row_number: int) -> str:
    """Get a single passenger by their row number (1-based).

    Returns all fields with resolved labels for the specified passenger.

    Examples:
        - row_number=1 → first passenger (Mr. Owen Harris Braund, Third class, male)
        - row_number=2 → Mrs. John Bradley Cumings, First class, female

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

    logger.info(
        "tool.get_passenger",
        row_number=row_number,
        duration_ms=round(duration_ms, 2),
    )
    return json.dumps(result, default=str)


def list_tables() -> str:
    """List all tables in the Titanic database with their schemas and row counts.

    Returns table names, column definitions (name, type, nullable), and row counts.
    Useful for understanding the normalized database structure.
    """
    start = time.monotonic()
    schemas = get_table_schemas()
    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "tool.list_tables",
        table_count=len(schemas),
        duration_ms=round(duration_ms, 2),
    )
    return json.dumps(schemas, default=str)
