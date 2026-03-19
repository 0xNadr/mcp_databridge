"""Full MCP protocol integration tests — spawns the real server via stdio.

These tests use the MCP SDK client to connect to the server as a subprocess,
performing the full JSON-RPC handshake exactly as a real AI agent would.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def _parse_tool_result(result) -> dict:
    """Extract parsed JSON from a tool call result."""
    return json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_full_mcp_protocol(tmp_path: Path) -> None:
    """End-to-end MCP protocol test — server registration, all tools, resources, prompts."""
    # Setup: copy DB for isolation
    source_db = Path(__file__).parent.parent / "data" / "titanic.db"
    test_db = tmp_path / "titanic.db"
    shutil.copy2(source_db, test_db)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_databridge"],
        env={"DATABRIDGE_DB_PATH": str(test_db), "DATABRIDGE_LOG_LEVEL": "WARNING"},
    )

    async with (
        stdio_client(server_params) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        # ---------------------------------------------------------------
        # Server registration
        # ---------------------------------------------------------------

        # All 7 tools registered
        tools = await session.list_tools()
        tool_names = sorted(t.name for t in tools.tools)
        assert tool_names == [
            "aggregate_stats",
            "describe_column",
            "get_passenger",
            "get_survival_analysis",
            "list_tables",
            "query_passengers",
            "run_sql",
        ], f"Expected 7 tools, got: {tool_names}"

        # Resources (2 static + 1 template)
        resources = await session.list_resources()
        resource_uris = sorted(str(r.uri) for r in resources.resources)
        assert "databridge://info" in resource_uris
        assert "databridge://sample" in resource_uris

        templates = await session.list_resource_templates()
        template_uris = [t.uriTemplate for t in templates.resourceTemplates]
        assert any("stats" in t for t in template_uris)

        # All 3 prompts registered
        prompts = await session.list_prompts()
        prompt_names = sorted(p.name for p in prompts.prompts)
        assert prompt_names == [
            "data_quality_report",
            "explore_dataset",
            "survival_analysis",
        ]

        # ---------------------------------------------------------------
        # Tools: list_tables
        # ---------------------------------------------------------------
        result = await session.call_tool("list_tables", {})
        data = _parse_tool_result(result)
        table_names = [t["table"] for t in data]
        assert len(data) == 8
        assert "Observation" in table_names

        # ---------------------------------------------------------------
        # Tools: query_passengers
        # ---------------------------------------------------------------
        result = await session.call_tool("query_passengers", {"limit": 5})
        data = _parse_tool_result(result)
        assert data["count"] == 5
        row = data["rows"][0]
        assert row["sex"] in ("male", "female")  # resolved labels
        assert "class" in row

        # With filters
        result = await session.call_tool(
            "query_passengers",
            {"filters": {"sex": "female", "pclass": 1}, "limit": 10},
        )
        data = _parse_tool_result(result)
        assert data["count"] > 0
        for row in data["rows"]:
            assert row["sex"] == "female"
            assert row["pclass"] == 1

        # Invalid filter
        result = await session.call_tool("query_passengers", {"filters": {"nonexistent": "value"}})
        data = _parse_tool_result(result)
        assert "error" in data

        # ---------------------------------------------------------------
        # Tools: get_passenger
        # ---------------------------------------------------------------
        result = await session.call_tool("get_passenger", {"row_number": 1})
        data = _parse_tool_result(result)
        assert data["row_number"] == 1
        assert "sex" in data and "class" in data

        # Invalid row
        result = await session.call_tool("get_passenger", {"row_number": 0})
        data = _parse_tool_result(result)
        assert "error" in data

        # ---------------------------------------------------------------
        # Tools: aggregate_stats
        # ---------------------------------------------------------------
        result = await session.call_tool(
            "aggregate_stats",
            {"group_by": "class", "metric": "avg", "column": "fare"},
        )
        data = _parse_tool_result(result)
        assert data["count"] == 3
        fares = {r["class"]: r["avg_fare"] for r in data["results"]}
        assert fares["First"] > fares["Second"] > fares["Third"]

        # Invalid metric
        result = await session.call_tool(
            "aggregate_stats",
            {"group_by": "sex", "metric": "bad", "column": "survived"},
        )
        data = _parse_tool_result(result)
        assert "error" in data

        # ---------------------------------------------------------------
        # Tools: get_survival_analysis
        # ---------------------------------------------------------------
        result = await session.call_tool("get_survival_analysis", {"dimension": "sex"})
        data = _parse_tool_result(result)
        assert data["dimension"] == "sex"
        assert len(data["results"]) == 2
        rates = {r["sex"]: r["survival_rate_pct"] for r in data["results"]}
        assert rates["female"] > rates["male"]

        # Age groups
        result = await session.call_tool("get_survival_analysis", {"dimension": "age_group"})
        data = _parse_tool_result(result)
        assert data["dimension"] == "age_group"
        assert len(data["results"]) > 0

        # Invalid dimension
        result = await session.call_tool("get_survival_analysis", {"dimension": "invalid"})
        data = _parse_tool_result(result)
        assert "error" in data

        # ---------------------------------------------------------------
        # Tools: describe_column
        # ---------------------------------------------------------------
        result = await session.call_tool("describe_column", {"column": "age"})
        data = _parse_tool_result(result)
        assert data["type"] == "numeric"
        assert "mean" in data and "median" in data

        result = await session.call_tool("describe_column", {"column": "sex"})
        data = _parse_tool_result(result)
        assert data["type"] == "categorical"

        # ---------------------------------------------------------------
        # Tools: run_sql
        # ---------------------------------------------------------------
        result = await session.call_tool(
            "run_sql",
            {"query": "SELECT COUNT(*) as cnt FROM Observation"},
        )
        data = _parse_tool_result(result)
        assert data["rows"][0]["cnt"] == 891

        # Blocked: DROP
        result = await session.call_tool("run_sql", {"query": "DROP TABLE Observation"})
        data = _parse_tool_result(result)
        assert "error" in data

        # Blocked: INSERT
        result = await session.call_tool("run_sql", {"query": "INSERT INTO Observation VALUES (1)"})
        data = _parse_tool_result(result)
        assert "error" in data

        # ---------------------------------------------------------------
        # Resources
        # ---------------------------------------------------------------
        result = await session.read_resource("databridge://info")
        data = json.loads(result.contents[0].text)
        assert data["name"] == "Titanic Passenger Dataset"
        assert len(data["tables"]) == 8

        result = await session.read_resource("databridge://sample")
        data = json.loads(result.contents[0].text)
        assert len(data) == 5
        assert "sex" in data[0]

        result = await session.read_resource("databridge://stats/age")
        data = json.loads(result.contents[0].text)
        assert data["type"] == "numeric"

        # ---------------------------------------------------------------
        # Prompts
        # ---------------------------------------------------------------
        prompt = await session.get_prompt("explore_dataset")
        assert "list_tables" in prompt.messages[0].content.text

        prompt = await session.get_prompt("survival_analysis")
        assert "survival" in prompt.messages[0].content.text.lower()

        prompt = await session.get_prompt("data_quality_report")
        assert "missing" in prompt.messages[0].content.text.lower()

        # ---------------------------------------------------------------
        # Workflow: first-class women survival rate
        # ---------------------------------------------------------------
        result = await session.call_tool(
            "query_passengers",
            {"filters": {"sex": "female", "pclass": 1}, "limit": 200},
        )
        data = _parse_tool_result(result)
        rows = data["rows"]
        survived = sum(1 for r in rows if r["survived"] == 1)
        rate = survived / len(rows)
        assert rate > 0.9, f"Expected >90% survival, got {rate:.1%}"

        # ---------------------------------------------------------------
        # Workflow: explore → describe → custom SQL
        # ---------------------------------------------------------------
        result = await session.call_tool("describe_column", {"column": "fare"})
        stats = _parse_tool_result(result)
        assert stats["type"] == "numeric"
        assert stats["max"] > 0

        result = await session.call_tool(
            "run_sql",
            {"query": "SELECT AVG(age) as avg_age FROM Observation WHERE survived = 1"},
        )
        data = _parse_tool_result(result)
        assert data["rows"][0]["avg_age"] > 0
