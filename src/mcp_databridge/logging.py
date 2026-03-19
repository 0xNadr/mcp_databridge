"""Structured logging configuration via structlog with correlation IDs."""

from __future__ import annotations

import logging
import sys
import uuid

import structlog

from mcp_databridge.config import settings


def add_correlation_id(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Add a correlation ID to each log entry if not already present."""
    if "correlation_id" not in event_dict:
        event_dict["correlation_id"] = str(uuid.uuid4())[:8]
    return event_dict


def setup_logging() -> None:
    """Configure structlog for JSON output to stderr (stdout reserved for MCP protocol)."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_correlation_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
