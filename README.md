# MCP DataBridge

Production-ready MCP server that enables AI agents to interact with the Titanic passenger database via the [Model Context Protocol](https://modelcontextprotocol.io/).

## Architecture

```
┌──────────────┐         MCP Protocol         ┌──────────────────────────────┐
│   AI Agent   │◄────── stdio / HTTP ────────►│       MCP DataBridge         │
│ (Claude, etc)│                              │                              │
└──────────────┘                              │  Tools ─── query_passengers  │
                                              │          ├ get_passenger     │
                                              │          ├ aggregate_stats   │
                                              │          ├ survival_analysis │
                                              │          ├ describe_column   │
                                              │          ├ list_tables       │
                                              │          └ run_sql (sandbox) │
                                              │                              │
                                              │  Resources ─ info, sample,   │
                                              │              stats/{column}  │
                                              │                              │
                                              │  Prompts ── explore_dataset  │
                                              │           ├ survival_analysis│
                                              │           └ data_quality     │
                                              │                              │
                                              │  ┌────────────────────────┐  │
                                              │  │  SQLite (8 tables)     │  │
                                              │  │  891 passengers        │  │
                                              │  │  Normalized + JOINs    │  │
                                              │  └────────────────────────┘  │
                                              └──────────────────────────────┘
```

**Database**: 891 passengers across 8 normalized tables (Observation + 7 lookup tables). All tools resolve foreign keys and return human-readable labels — agents never see raw IDs.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run (stdio transport — for MCP clients like Claude Desktop)
python -m mcp_databridge

# Run with HTTP transport (for remote/Docker access)
DATABRIDGE_TRANSPORT=streamable-http python -m mcp_databridge

# Open MCP Inspector (interactive web UI for testing tools/resources/prompts)
npx @modelcontextprotocol/inspector --config inspector-config.json --server databridge
```

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) and add the `mcpServers` block:

```json
{
  "mcpServers": {
    "databridge": {
      "command": "/full/path/to/python",
      "args": ["-m", "mcp_databridge"],
      "cwd": "/path/to/mcp_databridge",
      "env": {
        "DATABRIDGE_DB_PATH": "/path/to/mcp_databridge/data/titanic.db"
      }
    }
  }
}
```

> **Important**: Use the full Python path (run `which python` to find it). Claude Desktop does not inherit your shell's `PATH`, so bare `python` won't be found. The `DATABRIDGE_DB_PATH` env var ensures the database is found regardless of working directory.

Then quit Claude Desktop (Cmd+Q) and reopen it. The server should appear under **Connectors**.

### VS Code

Add to your VS Code MCP settings (`.vscode/mcp.json` or user settings):

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
# HTTP transport (accessible at http://localhost:8000/mcp)
docker compose up -d

# stdio transport (pipe directly to MCP client)
docker build -t mcp-databridge .
docker run -i mcp-databridge
```

To connect Claude Desktop to the Docker container, edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "databridge": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Then quit Claude Desktop (Cmd+Q) and reopen it. View server logs with `docker logs -f databridge`.

## Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `query_passengers` | Filter and retrieve passengers with resolved labels | `filters`, `columns`, `limit`, `offset` |
| `get_passenger` | Get a single passenger by row number (1–891) | `row_number` |
| `aggregate_stats` | Group-by aggregations (count/avg/sum/min/max) | `group_by`, `metric`, `column` |
| `get_survival_analysis` | Survival rates by class, sex, age group, deck, etc. | `dimension` |
| `describe_column` | Statistical summary for any column | `column` |
| `list_tables` | Show all tables and their schemas | — |
| `run_sql` | Execute read-only SQL (SELECT only, sandboxed) | `query` |

### Filter Syntax

Filters use human-readable labels. The server resolves them to foreign key JOINs internally:

```json
{
  "sex": "female",
  "pclass": 1,
  "age_min": 20,
  "age_max": 40,
  "survived": true,
  "embarked": "S",
  "who": "woman",
  "deck": "B",
  "alone": false
}
```

Use `"missing"` to filter for unknown/NULL values in categorical columns:

```json
{"deck": "missing"}
{"embarked": "missing"}
{"embark_town": "missing"}
```

## Resources

| URI | Description |
|-----|-------------|
| `databridge://info` | Schema, row counts, missing values, table relationships |
| `databridge://sample` | First 5 rows with resolved labels |
| `databridge://stats/{column}` | Statistical summary for a column (numeric or categorical) |

## Prompts

| Prompt | Description |
|--------|-------------|
| `explore_dataset` | Guided exploration — schema overview, suggested starting queries |
| `survival_analysis` | Step-by-step survival analysis across multiple dimensions |
| `data_quality_report` | Missing values, distributions, data quality findings |

## Example Agent Interaction

> **User**: "What was the survival rate for women vs men?"

Agent calls `get_survival_analysis(dimension="sex")`:

```json
{
  "dimension": "sex",
  "results": [
    {"sex": "female", "survived_count": 233, "total_count": 314, "survival_rate_pct": 74.2},
    {"sex": "male", "survived_count": 109, "total_count": 577, "survival_rate_pct": 18.89}
  ]
}
```

> **User**: "Average fare by passenger class?"

Agent calls `aggregate_stats(group_by="class", metric="avg", column="fare")`:

```json
{
  "results": [
    {"class": "First", "avg_fare": 84.15},
    {"class": "Second", "avg_fare": 20.66},
    {"class": "Third", "avg_fare": 13.68}
  ],
  "count": 3
}
```

> **User**: "Show me first-class female passengers"

Agent calls `query_passengers(filters={"sex": "female", "pclass": 1})`:

```json
{
  "rows": [
    {
      "row_number": 2, "survived": 1, "pclass": 1, "age": 38.0,
      "sex": "female", "class": "First", "who": "woman",
      "deck": "C", "embark_town": "Cherbourg", "fare": 71.28, "alive": "yes"
    }
  ],
  "count": 94
}
```

All responses use **human-readable labels** (e.g., `"female"`, `"First"`, `"Cherbourg"`) — the normalized schema is fully abstracted from the agent.

## Configuration

All settings via environment variables (12-factor compliant):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABRIDGE_DB_PATH` | `./data/titanic.db` | Path to SQLite database |
| `DATABRIDGE_LOG_LEVEL` | `INFO` | Logging level |
| `DATABRIDGE_MAX_RESULTS` | `200` | Max rows per query |
| `DATABRIDGE_TRANSPORT` | `stdio` | Transport: `stdio` \| `streamable-http` |
| `DATABRIDGE_HOST` | `0.0.0.0` | HTTP host (streamable-http only) |
| `DATABRIDGE_PORT` | `8000` | HTTP port (streamable-http only) |
| `DATABRIDGE_QUERY_TIMEOUT` | `30` | Query timeout in seconds |

## Security

- **Read-only SQL**: `run_sql` only allows SELECT — DDL/DML keywords (DROP, INSERT, UPDATE, DELETE, ALTER, CREATE, ATTACH, DETACH, PRAGMA) are blocked
- **Parameterized queries**: All built-in tools use parameterized queries to prevent SQL injection
- **Input validation**: All tool parameters validated via Pydantic models with constrained types
- **Result size limits**: Max 200 rows per query (configurable)
- **Non-root container**: Docker runs as unprivileged `appuser`
- **Multi-statement blocking**: Semicolons in `run_sql` queries are rejected

## Testing

```bash
# Run all tests (119 tests, 95% coverage)
pytest --cov=mcp_databridge --cov-report=term-missing -v

# Lint + format check
ruff check src/ tests/
ruff format --check src/ tests/

# Type check
mypy src/

# Interactive MCP Inspector (pre-configured command, args, env vars)
npx @modelcontextprotocol/inspector --config inspector-config.json --server databridge
```

**Test suite includes:**
- Unit tests for all 7 tools, 3 resources, 3 prompts
- Database layer tests (connection management, query helpers, SQL sandbox)
- Pydantic model validation tests
- Full MCP protocol integration test (spawns server via stdio, performs JSON-RPC handshake, tests all endpoints)
- Structured logging tests (correlation IDs, log configuration)

## Project Structure

```
mcp_databridge/
├── pyproject.toml              # Dependencies, tool config (ruff, mypy, pytest)
├── Dockerfile                  # Production container (non-root, slim)
├── docker-compose.yml          # HTTP transport deployment
├── inspector-config.json       # Pre-configured MCP Inspector (command, args, env vars)
├── .github/workflows/ci.yml    # CI: lint → type-check → test (3.11-3.13) → docker build
├── .env.example                # Configuration template
├── data/
│   └── titanic.db              # Pre-built SQLite database (committed)
├── src/mcp_databridge/
│   ├── __main__.py             # Entry point: python -m mcp_databridge
│   ├── server.py               # FastMCP server — registers tools, resources, prompts
│   ├── database.py             # SQLite connection, resolved-view JOINs, SQL sandbox
│   ├── models.py               # Pydantic models for parameter validation
│   ├── config.py               # pydantic-settings (env vars with DATABRIDGE_ prefix)
│   ├── logging.py              # structlog JSON logging with correlation IDs
│   ├── resources.py            # MCP resources (info, sample, stats)
│   ├── prompts.py              # MCP prompts (explore, survival, quality)
│   └── tools/
│       ├── query.py            # query_passengers, get_passenger, list_tables
│       ├── analytics.py        # aggregate_stats, get_survival_analysis, describe_column
│       └── sql.py              # run_sql (sandboxed, SELECT-only)
└── tests/
    ├── conftest.py             # Shared fixtures (test DB copy)
    ├── test_tools/             # Unit tests for each tool module
    ├── test_database.py        # Database layer tests
    ├── test_resources.py       # Resource endpoint tests
    ├── test_prompts.py         # Prompt content tests
    ├── test_models.py          # Pydantic validation tests
    ├── test_logging.py         # Logging configuration tests
    ├── test_server.py          # Server wiring tests
    ├── test_integration.py     # Integration tests
    └── test_mcp_protocol.py    # Full MCP protocol round-trip via stdio
```

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.11+ | Challenge requirement |
| MCP SDK | FastMCP (mcp v1.26+) | Official Anthropic SDK, decorator-based registration |
| Database | SQLite (stdlib sqlite3) | Zero-infra, pre-built database, WAL mode for concurrent reads |
| Validation | Pydantic v2 | Type safety, constrained types, serialization |
| Config | pydantic-settings | 12-factor env var management with type coercion |
| Logging | structlog | Structured JSON logging, correlation IDs |
| Testing | pytest + pytest-asyncio | 119 tests, 95% coverage, MCP protocol integration |
| Linting | Ruff | Fast, replaces flake8 + isort + pyupgrade |
| Type Check | mypy (strict mode) | Static analysis, catches bugs before runtime |
| Container | Docker (slim) | Non-root, minimal image, stdio + HTTP transport |
| CI/CD | GitHub Actions | lint → type-check → test (3.11/3.12/3.13) → docker build |
