"""Database connection management and query helpers for the normalized Titanic schema."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any

import structlog

from mcp_databridge.config import settings

logger = structlog.get_logger()

# SQL for a fully-resolved view that JOINs all lookup tables
RESOLVED_VIEW_SQL = """
    SELECT
        o.rowid AS row_number,
        o.survived,
        o.pclass,
        o.age,
        o.sibsp,
        o.parch,
        o.fare,
        o.adult_male,
        o.alone,
        s.sex,
        e.embarked,
        c.class AS class,
        w.who,
        d.deck,
        et.embark_town,
        a.alive
    FROM Observation o
    LEFT JOIN Sex s ON o.sex_id = s.sex_id
    LEFT JOIN Embarked e ON o.embarked_id = e.embarked_id
    LEFT JOIN Class c ON o.class_id = c.class_id
    LEFT JOIN Who w ON o.who_id = w.who_id
    LEFT JOIN Deck d ON o.deck_id = d.deck_id
    LEFT JOIN EmbarkTown et ON o.embark_town_id = et.embark_town_id
    LEFT JOIN Alive a ON o.alive_id = a.alive_id
"""

# Mapping from human-readable filter keys to SQL conditions
FILTER_CONDITIONS: dict[str, str] = {
    "survived": "o.survived = ?",
    "pclass": "o.pclass = ?",
    "age_min": "o.age >= ?",
    "age_max": "o.age <= ?",
    "sibsp": "o.sibsp = ?",
    "parch": "o.parch = ?",
    "fare_min": "o.fare >= ?",
    "fare_max": "o.fare <= ?",
    "adult_male": "o.adult_male = ?",
    "alone": "o.alone = ?",
    "sex": "s.sex = ?",
    "embarked": "e.embarked = ?",
    "class": "c.class = ?",
    "who": "w.who = ?",
    "deck": "d.deck = ?",
    "embark_town": "et.embark_town = ?",
    "alive": "a.alive = ?",
}


def _get_db_path() -> str:
    """Resolve the database path, checking it exists."""
    db_path = settings.db_path
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")
    return str(db_path)


@contextmanager
def get_connection() -> Any:
    """Get a SQLite connection with WAL mode and timeout."""
    conn = sqlite3.connect(
        _get_db_path(),
        timeout=settings.query_timeout,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def query_resolved(
    filters: dict[str, Any] | None = None,
    columns: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Query passengers with fully resolved labels.

    Args:
        filters: Human-readable filter dict (e.g., {"sex": "female", "pclass": 1}).
        columns: Optional list of columns to return. Returns all if None.
        limit: Max rows to return (capped at settings.max_results).
        offset: Number of rows to skip.

    Returns:
        List of passenger dicts with resolved labels.
    """
    limit = min(limit, settings.max_results)
    where_clauses: list[str] = []
    params: list[Any] = []

    if filters:
        for key, value in filters.items():
            if key not in FILTER_CONDITIONS:
                raise ValueError(f"Unknown filter key: {key!r}. Valid keys: {sorted(FILTER_CONDITIONS)}")
            where_clauses.append(FILTER_CONDITIONS[key])
            # Convert booleans to int for SQLite
            if isinstance(value, bool):
                params.append(int(value))
            else:
                params.append(value)

    sql = RESOLVED_VIEW_SQL
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    sql += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()

    results = [dict(row) for row in rows]

    if columns:
        valid_columns = set(results[0].keys()) if results else set()
        invalid = set(columns) - valid_columns
        if invalid:
            raise ValueError(f"Unknown columns: {invalid}. Valid: {sorted(valid_columns)}")
        results = [{k: v for k, v in row.items() if k in columns} for row in results]

    logger.debug("query_resolved", row_count=len(results), filters=filters)
    return results


def get_passenger_by_rowid(row_number: int) -> dict[str, Any] | None:
    """Get a single passenger by 1-based row number."""
    sql = RESOLVED_VIEW_SQL + " WHERE o.rowid = ?"
    with get_connection() as conn:
        cursor = conn.execute(sql, [row_number])
        row = cursor.fetchone()
    return dict(row) if row else None


def get_table_schemas() -> list[dict[str, Any]]:
    """Get all table names and their schemas."""
    with get_connection() as conn:
        tables_cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in tables_cursor.fetchall()]

        result = []
        for table in tables:
            col_cursor = conn.execute(f"PRAGMA table_info({table})")  # noqa: S608
            columns = [
                {
                    "name": col["name"],
                    "type": col["type"],
                    "nullable": not col["notnull"],
                    "primary_key": bool(col["pk"]),
                }
                for col in col_cursor.fetchall()
            ]
            count_cursor = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}")  # noqa: S608
            count = count_cursor.fetchone()["cnt"]
            result.append({"table": table, "columns": columns, "row_count": count})

    return result


def execute_readonly_sql(query: str) -> list[dict[str, Any]]:
    """Execute a read-only SQL query with safety checks.

    Only SELECT statements are allowed. DDL/DML is rejected.
    """
    stripped = query.strip().rstrip(";").strip()
    # Check for multiple statements
    if ";" in stripped:
        raise ValueError("Multiple SQL statements are not allowed")

    # Only allow SELECT
    first_word = stripped.split()[0].upper() if stripped else ""
    if first_word != "SELECT":
        raise ValueError(f"Only SELECT queries are allowed, got: {first_word}")

    # Block dangerous keywords that could appear in subqueries or CTEs
    upper = stripped.upper()
    blocked = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "ATTACH", "DETACH", "PRAGMA"]
    for keyword in blocked:
        if keyword in upper.split():
            raise ValueError(f"Forbidden keyword in query: {keyword}")

    sql = f"{stripped} LIMIT {settings.max_results}"

    with get_connection() as conn:
        try:
            cursor = conn.execute(sql)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            raise ValueError(f"SQL execution error: {e}") from e

    return [dict(row) for row in rows]


def get_column_stats(column: str) -> dict[str, Any]:
    """Get statistical summary for a column in the resolved view."""
    # Numeric columns from Observation
    numeric_cols = {"age", "fare", "sibsp", "parch", "pclass", "survived", "adult_male", "alone"}
    # Categorical columns from lookup tables
    categorical_cols = {"sex", "embarked", "class", "who", "deck", "embark_town", "alive"}

    all_cols = numeric_cols | categorical_cols
    if column not in all_cols:
        raise ValueError(f"Unknown column: {column!r}. Valid: {sorted(all_cols)}")

    resolved_cte = f"WITH resolved AS ({RESOLVED_VIEW_SQL})"

    with get_connection() as conn:
        if column in numeric_cols:
            sql = f"""
                {resolved_cte}
                SELECT
                    COUNT({column}) as count,
                    COUNT(*) - COUNT({column}) as missing,
                    MIN({column}) as min,
                    MAX({column}) as max,
                    AVG({column}) as mean,
                    SUM({column}) as sum
                FROM resolved
            """
            cursor = conn.execute(sql)
            stats = dict(cursor.fetchone())

            # Median
            median_sql = f"""
                {resolved_cte}
                SELECT {column} as median
                FROM resolved
                WHERE {column} IS NOT NULL
                ORDER BY {column}
                LIMIT 1
                OFFSET (SELECT COUNT({column}) FROM resolved WHERE {column} IS NOT NULL) / 2
            """
            median_cursor = conn.execute(median_sql)
            median_row = median_cursor.fetchone()
            stats["median"] = median_row["median"] if median_row else None
            stats["column"] = column
            stats["type"] = "numeric"
            return stats
        else:
            sql = f"""
                {resolved_cte}
                SELECT
                    {column} as value,
                    COUNT(*) as count
                FROM resolved
                GROUP BY {column}
                ORDER BY count DESC
            """
            cursor = conn.execute(sql)
            distribution = [dict(row) for row in cursor.fetchall()]

            total = sum(d["count"] for d in distribution)
            missing = sum(d["count"] for d in distribution if d["value"] is None or d["value"] == "")
            return {
                "column": column,
                "type": "categorical",
                "total": total,
                "missing": missing,
                "unique_values": len(distribution),
                "distribution": distribution,
            }


def aggregate(
    group_by: str,
    metric: str,
    column: str,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run an aggregation query on the resolved view.

    Args:
        group_by: Column to group by (e.g., "sex", "pclass", "class").
        metric: Aggregation function (count, avg, sum, min, max).
        column: Column to aggregate.
        filters: Optional filters (same syntax as query_resolved).
    """
    valid_metrics = {"count", "avg", "sum", "min", "max"}
    if metric.lower() not in valid_metrics:
        raise ValueError(f"Invalid metric: {metric!r}. Valid: {sorted(valid_metrics)}")

    all_cols = {
        "age", "fare", "sibsp", "parch", "pclass", "survived",
        "adult_male", "alone", "sex", "embarked", "class", "who",
        "deck", "embark_town", "alive", "row_number",
    }
    if group_by not in all_cols:
        raise ValueError(f"Unknown group_by column: {group_by!r}")
    if column not in all_cols:
        raise ValueError(f"Unknown column: {column!r}")

    resolved_cte = f"WITH resolved AS ({RESOLVED_VIEW_SQL})"

    where_clauses: list[str] = []
    params: list[Any] = []
    if filters:
        for key, value in filters.items():
            if key not in FILTER_CONDITIONS:
                raise ValueError(f"Unknown filter key: {key!r}")
            # Remap filter conditions to use resolved CTE column names
            condition = FILTER_CONDITIONS[key]
            # Replace table aliases with direct column refs for CTE
            for alias in ["o.", "s.", "e.", "c.", "w.", "d.", "et.", "a."]:
                condition = condition.replace(alias, "")
            where_clauses.append(condition)
            if isinstance(value, bool):
                params.append(int(value))
            else:
                params.append(value)

    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)

    metric_fn = metric.upper()
    sql = f"""
        {resolved_cte}
        SELECT {group_by}, {metric_fn}({column}) as {metric}_{column}
        FROM resolved
        {where_sql}
        GROUP BY {group_by}
        ORDER BY {metric_fn}({column}) DESC
    """

    with get_connection() as conn:
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            raise ValueError(f"Aggregation error: {e}") from e

    return [dict(row) for row in rows]
