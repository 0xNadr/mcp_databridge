"""Tests for MCP prompts."""

from __future__ import annotations

from mcp_databridge.prompts import (
    data_quality_report,
    explore_dataset,
    survival_analysis,
)


class TestPrompts:
    def test_explore_dataset_returns_string(self) -> None:
        result = explore_dataset()
        assert isinstance(result, str)
        assert "list_tables" in result
        assert "891" in result

    def test_survival_analysis_returns_string(self) -> None:
        result = survival_analysis()
        assert isinstance(result, str)
        assert "survival" in result.lower()
        assert "get_survival_analysis" in result

    def test_data_quality_report_returns_string(self) -> None:
        result = data_quality_report()
        assert isinstance(result, str)
        assert "missing" in result.lower()
        assert "deck" in result.lower()
