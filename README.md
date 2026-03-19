# MCP DataBridge

Production-ready MCP server that enables AI agents to interact with the Titanic passenger database via the [Model Context Protocol](https://modelcontextprotocol.io/).

## Architecture

```
┌──────────────┐         MCP Protocol         ┌──────────────────┐
│   AI Agent   │◄────── stdio / HTTP ────────►│  MCP DataBridge  │
│ (Claude, etc)│                               │                  │
└──────────────┘                               │  7 Tools         │
                                               │  3 Resources     │
                                               │  3 Prompts       │
                                               │                  │
                                               │  ┌────────────┐  │
                                               │  │  SQLite DB  │  │
                                               │  │  (Titanic)  │  │
                                               │  └────────────┘  │
                                               └──────────────────┘
```

**Database**: 891 passengers across 8 normalized tables (Observation + 7 lookup tables). All tools return human-readable labels — no raw foreign key IDs.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run (stdio transport — for MCP clients)
python -m mcp_databridge

# Or use the CLI entry point
mcp-databridge
```

### Claude Desktop / VS Code Integration

Add to your MCP client config:

```json
{
  "mcpServers": {
    "databridge": {
      "command": "python",
      "args": ["-m", "mcp_databridge"],
      "cwd": "/path/to/mcp_databridge"
    }
  }
}
```

### Docker

```bash
# stdio transport
docker build -t mcp-databridge .
docker run -i mcp-databridge

# HTTP transport
docker compose up
# Server available at http://localhost:8000
```

## Tools

| Tool | Description |
|------|-------------|
| `query_passengers` | Filter and retrieve passengers with human-readable labels |
| `get_passenger` | Get a single passenger by row number (1-891) |
| `aggregate_stats` | Group-by aggregations (count/avg/sum/min/max) |
| `get_survival_analysis` | Survival rates by class, sex, age group, deck, etc. |
| `describe_column` | Statistical summary for any column |
| `list_tables` | Show all tables and their schemas |
| `run_sql` | Execute read-only SQL (SELECT only, sandboxed) |

### Example Queries an Agent Can Answer

- "What was the survival rate for first-class female passengers?"
- "Show me the average fare by passenger class"
- "How many children survived vs adults?"
- "Which deck had the best survival rate?"

### Filter Syntax

```json
{
  "sex": "female",
  "pclass": 1,
  "age_min": 20,
  "age_max": 40,
  "survived": true,
  "embarked": "S"
}
```

## Resources

| URI | Description |
|-----|-------------|
| `databridge://info` | Schema, row counts, missing values, table relationships |
| `databridge://sample` | First 5 rows with resolved labels |
| `databridge://stats/{column}` | Statistical summary for a column |

## Prompts

| Prompt | Description |
|--------|-------------|
| `explore_dataset` | Guided exploration walkthrough |
| `survival_analysis` | Step-by-step survival analysis workflow |
| `data_quality_report` | Missing values and data quality analysis |

## Configuration

All settings via environment variables (12-factor):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABRIDGE_DB_PATH` | `./data/titanic.db` | Path to SQLite database |
| `DATABRIDGE_LOG_LEVEL` | `INFO` | Logging level |
| `DATABRIDGE_MAX_RESULTS` | `200` | Max rows per query |
| `DATABRIDGE_TRANSPORT` | `stdio` | Transport: `stdio` or `streamable-http` |
| `DATABRIDGE_HOST` | `0.0.0.0` | HTTP host (streamable-http only) |
| `DATABRIDGE_PORT` | `8000` | HTTP port (streamable-http only) |
| `DATABRIDGE_QUERY_TIMEOUT` | `30` | Query timeout in seconds |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Run tests with coverage
pytest --cov=mcp_databridge --cov-report=term-missing

# Lint
ruff check src/ tests/

# Type check
mypy src/

# MCP Inspector (interactive testing)
mcp dev src/mcp_databridge/server.py
```

## Project Structure

```
src/mcp_databridge/
├── server.py       # FastMCP server — tools, resources, prompts
├── database.py     # SQLite queries, resolved-view JOINs, SQL sandbox
├── models.py       # Pydantic models for validation
├── config.py       # Environment variable configuration
├── logging.py      # Structured JSON logging (structlog)
└── __main__.py     # Entry point
```

## Security

- `run_sql` only allows SELECT — DDL/DML keywords are blocked
- All built-in tools use parameterized queries (no SQL injection)
- All inputs validated via Pydantic models
- Result sets capped at 200 rows
- Non-root user in Docker container

## Tech Stack

Python 3.11+ | FastMCP | SQLite | SQLAlchemy | Pydantic | structlog | pytest | Ruff | Docker | GitHub Actions
