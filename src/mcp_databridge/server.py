"""MCP DataBridge server — FastMCP server definition, wiring tools/resources/prompts."""

from __future__ import annotations

import structlog
from mcp.server.fastmcp import FastMCP

from mcp_databridge.config import settings
from mcp_databridge.logging import setup_logging
from mcp_databridge.prompts import (
    data_quality_report,
    explore_dataset,
    survival_analysis,
)
from mcp_databridge.resources import (
    column_stats_resource,
    dataset_info,
    dataset_sample,
)
from mcp_databridge.tools.analytics import (
    aggregate_stats,
    describe_column,
    get_survival_analysis,
)
from mcp_databridge.tools.query import get_passenger, list_tables, query_passengers
from mcp_databridge.tools.sql import run_sql

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
    host=settings.host,
    port=settings.port,
)


# --- Tools ---

mcp.tool()(query_passengers)
mcp.tool()(get_passenger)
mcp.tool()(list_tables)
mcp.tool()(aggregate_stats)
mcp.tool()(get_survival_analysis)
mcp.tool()(describe_column)
mcp.tool()(run_sql)

# --- Resources ---

mcp.resource("databridge://info")(dataset_info)
mcp.resource("databridge://sample")(dataset_sample)
mcp.resource("databridge://stats/{column}")(column_stats_resource)

# --- Prompts ---

mcp.prompt()(explore_dataset)
mcp.prompt()(survival_analysis)
mcp.prompt()(data_quality_report)


def main() -> None:
    """Run the MCP DataBridge server."""
    logger.info(
        "server.starting",
        transport=settings.transport,
        db_path=str(settings.db_path),
    )
    mcp.run(transport=settings.transport)
