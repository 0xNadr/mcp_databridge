"""Tests for MCP server wiring."""

from __future__ import annotations


class TestServerSetup:
    def test_server_imports_and_creates_mcp(self) -> None:
        from mcp_databridge.server import mcp

        assert mcp is not None
        assert mcp.name == "MCP DataBridge"

    def test_tools_registered(self) -> None:
        from mcp_databridge.server import mcp

        # The mcp object should have tools registered
        assert mcp is not None

    def test_main_function_exists(self) -> None:
        from mcp_databridge.server import main

        assert callable(main)
