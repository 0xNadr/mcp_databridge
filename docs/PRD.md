# PRD: MCP DataBridge — Titanic Database MCP Server

## Context

A newly founded MLOps team needs a **production-ready Python MCP Server** that enables AI agents (operated by other teams) to interact with a database containing the Titanic dataset. This is a coding challenge for a job interview — the solution must demonstrate production-grade engineering practices and be presentable in ~1 week.

**Data source**: Pre-built SQLite database from [davidjamesknight/SQLite_databases_for_learning_data_science](https://github.com/davidjamesknight/SQLite_databases_for_learning_data_science/blob/main/titanic.db)

---

## 1. Product Overview

**MCP DataBridge** is a Python-based Model Context Protocol (MCP) server that exposes the Titanic dataset through standardized MCP tools, resources, and prompts. AI agents connect via MCP and can query, filter, aggregate, and analyze passenger data without writing raw SQL.

### Target Users
- **AI Agents** operated by other teams within the organization
- **Developers** integrating AI agents with internal data sources

### Key Value Proposition
- Standardized, secure database access for AI agents
- No SQL knowledge required by the agent — semantic tools handle the complexity
- Production-ready: observable, tested, containerized, documented

---

## 2. Technical Requirements

### 2.1 Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Broad compatibility, modern syntax |
| MCP SDK | `mcp` (FastMCP) v1.26+ | Official Anthropic SDK |
| Database | SQLite (provided .db file) | Pre-built, normalized, zero-infra |
| DB Access | sqlite3 (stdlib) | Zero-dependency, WAL mode, Row factory |
| Validation | Pydantic v2 | Type safety, serialization |
| Testing | pytest + pytest-cov | Industry standard |
| Linting | Ruff | Fast, comprehensive |
| Type Checking | mypy | Static analysis |
| Containerization | Docker + docker-compose | Deployment ready |
| CI/CD | GitHub Actions | Automated quality gates |
| Config | pydantic-settings (env vars) | 12-factor app compliance |
| Logging | structlog | Structured JSON logging |
| Transport | stdio (default), Streamable HTTP | Flexibility for different deployments |

### 2.2 Database Schema (provided — not modified)

The database is **normalized** across 8 tables with 891 passenger observations.

**Observation** (main fact table):
| Column | Type | Notes |
|--------|------|-------|
| survived | BIGINT | 0 = died, 1 = survived |
| pclass | BIGINT | Passenger class (1, 2, 3) |
| age | FLOAT | Nullable — 177 missing (20%) |
| sibsp | BIGINT | Siblings/spouses aboard |
| parch | BIGINT | Parents/children aboard |
| fare | FLOAT | Ticket fare in pounds |
| adult_male | BOOLEAN | 1 = adult male |
| alone | BOOLEAN | 1 = travelling alone |
| sex_id | BIGINT | FK → Sex |
| embarked_id | BIGINT | FK → Embarked (-1 = missing, 2 records) |
| class_id | BIGINT | FK → Class |
| who_id | BIGINT | FK → Who |
| deck_id | BIGINT | FK → Deck (-1 = missing, 688 records / 77%) |
| embark_town_id | BIGINT | FK → EmbarkTown (-1 = missing) |
| alive_id | BIGINT | FK → Alive |

**Lookup tables:**
| Table | Values |
|-------|--------|
| Sex | female, male |
| Embarked | C, Q, S (+ missing = -1) |
| Class | First, Second, Third |
| Who | child, man, woman |
| Deck | A, B, C, D, E, F, G (+ missing = -1) |
| EmbarkTown | Cherbourg, Queenstown, Southampton (+ missing = -1) |
| Alive | no, yes |

**Important design notes:**
- No `ROWID` alias or explicit primary key on Observation — SQLite provides implicit `rowid`
- Missing categorical values encoded as **-1 foreign keys**, not NULL
- No passenger names, ticket numbers, or cabin strings in this dataset
- `survived` (int) and `alive` (text) are redundant — both represent survival status

---

## 3. MCP Interface Design

### 3.1 Tools (Actions — AI agents call these)

| Tool | Description | Parameters |
|------|-------------|------------|
| `query_passengers` | Filter and retrieve passenger observations with resolved labels | `filters` (optional dict), `columns` (optional list), `limit` (int, default 50, max 200), `offset` (int, default 0) |
| `get_passenger` | Get a single passenger by row number | `row_number` (int, 1-based) |
| `aggregate_stats` | Run aggregation queries (count, avg, sum, min, max) | `group_by` (str), `metric` (str), `column` (str), `filters` (optional dict) |
| `get_survival_analysis` | Survival rate analysis by dimension | `dimension` (str: class/sex/embarked/age_group/deck/who/alone) |
| `describe_column` | Statistical summary for a numeric or categorical column | `column` (str) |
| `run_sql` | Execute read-only SQL (SELECT only) | `query` (str) — with SQL validation and safety checks |
| `list_tables` | Show all tables and their schemas | _(none)_ |

**Filter syntax** (for `query_passengers` and `aggregate_stats`):
```json
{
  "pclass": 1,
  "sex": "female",
  "age_min": 20,
  "age_max": 40,
  "survived": true,
  "embarked": "S",
  "who": "woman",
  "deck": "B",
  "alone": true,
  "adult_male": false
}
```

Filters use **human-readable labels** (e.g., `"sex": "female"`, not `"sex_id": 0`). The server resolves labels to IDs internally via JOINs. This abstracts the normalized schema for the AI agent.

**Tool response format** — all tools return resolved, human-readable data:
```json
{
  "survived": 1,
  "pclass": 1,
  "age": 38.0,
  "sex": "female",
  "embarked": "C",
  "class": "First",
  "who": "woman",
  "deck": "B",
  "embark_town": "Cherbourg",
  "alive": "yes",
  "sibsp": 1,
  "parch": 0,
  "fare": 71.28,
  "adult_male": false,
  "alone": false
}
```

### 3.2 Resources (Read-only data endpoints)

| Resource | URI | Description |
|----------|-----|-------------|
| Dataset info | `databridge://info` | Schema description, table list, row counts, missing value summary, relationships |
| Column stats | `databridge://stats/{column}` | Min, max, mean, median, distribution for a column |
| Dataset sample | `databridge://sample` | First 5 rows (fully resolved with labels) |

### 3.3 Prompts (Reusable templates)

| Prompt | Description |
|--------|-------------|
| `explore_dataset` | Guided exploration — explains the schema and suggests starting queries |
| `survival_analysis` | Step-by-step survival analysis workflow across multiple dimensions |
| `data_quality_report` | Analyze missing values (age, deck, embarked) and data quality |

---

## 4. Non-Functional Requirements

### 4.1 Security
- **Read-only SQL**: `run_sql` tool only allows SELECT statements; DDL/DML blocked via SQL parsing
- **Input validation**: All tool parameters validated via Pydantic models
- **SQL injection prevention**: Parameterized queries for built-in tools; `run_sql` uses statement-level validation
- **Query size limits**: Max result set size enforced (max 200 rows per query)

### 4.2 Observability
- **Structured logging** (JSON) via structlog — every tool call logged with duration, params, row count
- **Error tracking** with correlation IDs
- **Logs to stderr** — stdout reserved for MCP protocol communication

### 4.3 Configuration (12-Factor)
```env
DATABRIDGE_DB_PATH=./data/titanic.db       # Database file path
DATABRIDGE_LOG_LEVEL=INFO                   # Logging level
DATABRIDGE_MAX_RESULTS=200                  # Max rows per query
DATABRIDGE_TRANSPORT=stdio                  # Transport: stdio | streamable-http
DATABRIDGE_HOST=0.0.0.0                     # HTTP host (if streamable-http)
DATABRIDGE_PORT=8000                        # HTTP port (if streamable-http)
```

### 4.4 Performance
- SQLite with WAL mode for concurrent reads
- Context-managed connections via sqlite3 stdlib
- Result set size limits (max 200 rows per query)
- Lazy database initialization

### 4.5 Testing
- **Unit tests**: All tools, resources, prompts individually tested
- **Integration tests**: End-to-end tool interface tests with workflow scenarios
- **Coverage target**: >80%

### 4.6 Documentation
- README with quickstart, architecture diagram, configuration reference
- Inline docstrings on all public functions (consumed by MCP clients as tool descriptions)
- Example agent interaction transcript
- Contributing guide

---

## 5. Project Structure

```
mcp_databridge/
├── pyproject.toml              # Project metadata, dependencies, tool config
├── Dockerfile                  # Production container
├── docker-compose.yml          # Local dev environment
├── .github/
│   └── workflows/
│       └── ci.yml              # Lint, type-check, test, build
├── .env.example                # Configuration template
├── data/
│   └── titanic.db              # Pre-built SQLite database (committed)
├── docs/
│   └── PRD.md                  # This document
├── src/
│   └── mcp_databridge/
│       ├── __init__.py
│       ├── __main__.py         # Entry point: python -m mcp_databridge
│       ├── server.py           # FastMCP server definition + tool/resource/prompt registration
│       ├── config.py           # Pydantic settings
│       ├── database.py         # sqlite3 connection management, resolved-view queries
│       ├── models.py           # Pydantic models for tool params & responses
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── query.py        # query_passengers, get_passenger, list_tables
│       │   ├── analytics.py    # aggregate_stats, get_survival_analysis, describe_column
│       │   └── sql.py          # run_sql (sandboxed)
│       ├── resources.py        # MCP resources
│       ├── prompts.py          # MCP prompts
│       └── logging.py          # structlog configuration
├── tests/
│   ├── conftest.py             # Shared fixtures (test DB copy, MCP client)
│   ├── test_tools/
│   │   ├── test_query.py
│   │   ├── test_analytics.py
│   │   └── test_sql.py
│   ├── test_resources.py
│   ├── test_database.py
│   └── test_integration.py     # End-to-end MCP protocol tests
└── README.md
```

---

## 6. Implementation Phases

### Phase 1: Foundation (~2h)
- Project scaffolding (pyproject.toml, src layout, config)
- Database layer (sqlite3 connection, resolved-view query helpers for JOINs)
- Basic MCP server with FastMCP
- First tool: `query_passengers` with filter-to-JOIN resolution

### Phase 2: Core Tools (~2h)
- All 7 tools implemented with Pydantic validation
- SQL safety layer for `run_sql` (parse & reject non-SELECT)
- Label resolution layer: translate human-readable filters → FK lookups

### Phase 3: Resources & Prompts (~1h)
- 3 resources (info, stats, sample)
- 3 prompts (explore, survival analysis, data quality)

### Phase 4: Production Hardening (~1.5h)
- Structured logging throughout
- Error handling and correlation IDs
- Configuration management
- Query timeout enforcement

### Phase 5: Testing (~1h)
- Unit tests for all tools
- Integration tests
- Test fixtures and conftest

### Phase 6: Deployment & Docs (~0.5h)
- Dockerfile + docker-compose
- GitHub Actions CI pipeline
- README with architecture, quickstart, configuration

---

## 7. Success Criteria

1. An AI agent (e.g., Claude) can connect to the server and answer questions like:
   - "What was the survival rate for first-class female passengers?"
   - "What age group had the highest survival rate?"
   - "Show me the average fare by passenger class"
   - "How many children survived vs adults?"
   - "Which deck had the best survival rate?"
2. All tools return well-structured, human-readable JSON (no raw FK IDs)
3. Invalid inputs produce clear, actionable error messages
4. CI pipeline passes: lint + type-check + tests
5. Docker container builds and runs without configuration
6. README enables a new developer to get running in <5 minutes

---

## 8. Verification Plan

```bash
# 1. Install and run
pip install -e ".[dev]"
python -m mcp_databridge  # Should start on stdio

# 2. Run tests
pytest --cov=mcp_databridge --cov-report=term-missing

# 3. Lint & type-check
ruff check src/ tests/
mypy src/

# 4. Docker
docker build -t mcp-databridge .
docker run mcp-databridge

# 5. Manual MCP test (via mcp CLI or Inspector)
mcp dev src/mcp_databridge/server.py
```
