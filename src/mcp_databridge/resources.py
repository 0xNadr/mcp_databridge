"""MCP Resources: read-only data endpoints for the Titanic dataset."""

from __future__ import annotations

import json

from mcp_databridge.database import (
    get_column_stats,
    get_connection,
    get_table_schemas,
    query_resolved,
)


def dataset_info() -> str:
    """Titanic dataset overview: schema, relationships, row counts, missing values."""
    schemas = get_table_schemas()

    with get_connection() as conn:
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
            "Use the tools (query_passengers, aggregate_stats) for resolved data",
        ],
    }
    return json.dumps(info, indent=2, default=str)


def dataset_sample() -> str:
    """First 5 passengers with all labels resolved — a quick preview of the data."""
    rows = query_resolved(limit=5)
    return json.dumps(rows, indent=2, default=str)


def column_stats_resource(column: str) -> str:
    """Statistical summary for a specific column in the dataset."""
    try:
        stats = get_column_stats(column)
        return json.dumps(stats, indent=2, default=str)
    except ValueError as e:
        return json.dumps({"error": str(e)})
