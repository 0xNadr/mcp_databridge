"""Tests for structured logging configuration."""

from __future__ import annotations

import structlog

from mcp_databridge.logging import add_correlation_id, setup_logging


class TestCorrelationId:
    def test_adds_correlation_id(self) -> None:
        event_dict: structlog.types.EventDict = {"event": "test"}
        result = add_correlation_id(None, "info", event_dict)
        assert "correlation_id" in result
        assert len(result["correlation_id"]) == 8

    def test_preserves_existing_correlation_id(self) -> None:
        event_dict: structlog.types.EventDict = {
            "event": "test",
            "correlation_id": "existing",
        }
        result = add_correlation_id(None, "info", event_dict)
        assert result["correlation_id"] == "existing"


class TestSetupLogging:
    def test_setup_logging_configures_structlog(self) -> None:
        setup_logging()
        logger = structlog.get_logger()
        assert logger is not None
