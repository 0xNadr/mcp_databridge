"""SQL tool: run_sql (sandboxed, SELECT-only)."""

from __future__ import annotations

import json
import time

import structlog

from mcp_databridge.database import execute_readonly_sql

logger = structlog.get_logger()


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
