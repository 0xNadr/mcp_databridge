"""Integration tests — test MCP server tools via the server's tool interface."""

from __future__ import annotations

import json

from mcp_databridge.server import (
    aggregate_stats,
    describe_column,
    get_passenger,
    get_survival_analysis,
    list_tables,
    query_passengers,
    run_sql,
)


class TestToolEndToEnd:
    """Test tools as they would be called by an MCP client."""

    def test_query_passengers_no_filters(self) -> None:
        result = json.loads(query_passengers())
        assert "rows" in result
        assert result["count"] > 0
        assert result["count"] <= 50  # default limit

    def test_query_passengers_with_filters(self) -> None:
        result = json.loads(query_passengers(filters={"sex": "female", "pclass": 1}))
        assert result["count"] > 0
        for row in result["rows"]:
            assert row["sex"] == "female"
            assert row["pclass"] == 1

    def test_query_passengers_invalid_filter(self) -> None:
        result = json.loads(query_passengers(filters={"invalid": "value"}))
        assert "error" in result

    def test_get_passenger_valid(self) -> None:
        result = json.loads(get_passenger(1))
        assert "error" not in result
        assert result["row_number"] == 1

    def test_get_passenger_invalid(self) -> None:
        result = json.loads(get_passenger(0))
        assert "error" in result

    def test_list_tables(self) -> None:
        result = json.loads(list_tables())
        assert len(result) == 8

    def test_aggregate_stats(self) -> None:
        result = json.loads(aggregate_stats("sex", "avg", "survived"))
        assert "results" in result
        assert result["count"] == 2

    def test_aggregate_stats_invalid(self) -> None:
        result = json.loads(aggregate_stats("sex", "bad_metric", "survived"))
        assert "error" in result

    def test_survival_analysis(self) -> None:
        result = json.loads(get_survival_analysis("sex"))
        assert result["dimension"] == "sex"
        assert len(result["results"]) == 2

    def test_survival_analysis_age_group(self) -> None:
        result = json.loads(get_survival_analysis("age_group"))
        assert result["dimension"] == "age_group"
        assert len(result["results"]) > 0

    def test_survival_analysis_invalid(self) -> None:
        result = json.loads(get_survival_analysis("invalid"))
        assert "error" in result

    def test_describe_column(self) -> None:
        result = json.loads(describe_column("age"))
        assert result["type"] == "numeric"

    def test_run_sql(self) -> None:
        result = json.loads(run_sql("SELECT COUNT(*) as cnt FROM Observation"))
        assert result["rows"][0]["cnt"] == 891

    def test_run_sql_blocked(self) -> None:
        result = json.loads(run_sql("DROP TABLE Observation"))
        assert "error" in result


class TestWorkflows:
    """Test realistic AI agent workflows."""

    def test_survival_rate_first_class_women(self) -> None:
        result = json.loads(
            query_passengers(filters={"sex": "female", "pclass": 1}, limit=200)
        )
        rows = result["rows"]
        survived = sum(1 for r in rows if r["survived"] == 1)
        rate = survived / len(rows)
        assert rate > 0.9  # First class women had >90% survival

    def test_compare_class_fares(self) -> None:
        result = json.loads(aggregate_stats("class", "avg", "fare"))
        results = result["results"]
        fares = {r["class"]: r["avg_fare"] for r in results}
        assert fares["First"] > fares["Second"] > fares["Third"]

    def test_children_survival(self) -> None:
        result = json.loads(get_survival_analysis("who"))
        results = result["results"]
        rates = {r["who"]: r["survival_rate_pct"] for r in results}
        # Women had highest survival rate
        assert rates["woman"] > rates["man"]
