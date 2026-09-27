import pytest
import pandas as pd
from sqlalchemy import create_engine, text
from services.chart_service import chart_service
from agent.executor import execution_node
from agent.self_correction import self_correction_node
from agent.data_analysis import data_analysis_node
from agent.result_explainer import result_explainer_node
from agent.state import AgentState

def test_chart_selection_rules():
    # 1. Single scalar -> stat_card
    card_type, card_config = chart_service.select_chart(
        rows=[{"total_revenue": 450000.0}],
        columns=["total_revenue"]
    )
    assert card_type == "stat_card"
    assert "450,000" in card_config.get("value", "")

    # 2. Date column + numeric -> line chart
    line_type, line_config = chart_service.select_chart(
        rows=[
            {"order_date": "2023-01-01", "revenue": 1000},
            {"order_date": "2023-02-01", "revenue": 1500},
            {"order_date": "2023-03-01", "revenue": 1200}
        ],
        columns=["order_date", "revenue"]
    )
    assert line_type == "line"
    assert line_config["xKey"] == "order_date"
    assert "revenue" in line_config["yKeys"]

    # 3. Categorical (3 items) + numeric -> pie chart
    pie_type, pie_config = chart_service.select_chart(
        rows=[
            {"category": "Electronics", "sales": 5000},
            {"category": "Apparel", "sales": 3000},
            {"category": "Books", "sales": 2000}
        ],
        columns=["category", "sales"]
    )
    assert pie_type == "pie"
    assert pie_config["nameKey"] == "category"
    assert pie_config["dataKey"] == "sales"

    # 4. Many categories (> 5 items) + numeric -> bar chart
    bar_type, bar_config = chart_service.select_chart(
        rows=[
            {"city": f"City_{i}", "orders": i * 10} for i in range(8)
        ],
        columns=["city", "orders"]
    )
    assert bar_type == "bar"
    assert bar_config["xKey"] == "city"

@pytest.mark.asyncio
async def test_data_analysis_trends_and_outliers():
    # Test data with an obvious outlier: [10, 12, 11, 10, 13, 95]
    sample_rows = [
        {"order_date": "2023-01-01", "revenue": 10.0},
        {"order_date": "2023-02-01", "revenue": 12.0},
        {"order_date": "2023-03-01", "revenue": 11.0},
        {"order_date": "2023-04-01", "revenue": 10.0},
        {"order_date": "2023-05-01", "revenue": 13.0},
        {"order_date": "2023-06-01", "revenue": 95.0} # Outlier
    ]
    columns = ["order_date", "revenue"]

    state: AgentState = {
        "query_result": sample_rows,
        "column_names": columns
    }

    result = await data_analysis_node(state)
    analysis = result["analysis_result"]
    assert analysis is not None
    assert "summary_statistics" in analysis
    assert analysis["summary_statistics"]["revenue"]["sum"] == 151.0

    # Trend check
    assert len(analysis["trends"]) > 0
    assert analysis["trends"][0]["direction"] == "increased"

    # Outlier check
    assert len(analysis["outliers"]) > 0
    assert analysis["outliers"][0]["value"] == 95.0

@pytest.mark.asyncio
async def test_execution_node_success_and_failure():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE test_products (id INT, title TEXT, price FLOAT);"))
        conn.execute(text("INSERT INTO test_products VALUES (1, 'Widget', 29.99), (2, 'Gadget', 49.99);"))
        conn.commit()

    # 1. Successful execution
    success_state: AgentState = {
        "sanitized_sql": "SELECT * FROM test_products ORDER BY price DESC",
        "target_engine": engine
    }
    res = await execution_node(success_state)
    assert res["was_successful"] is True
    assert res["row_count"] == 2
    assert res["column_names"] == ["id", "title", "price"]
    assert res["query_result"][0]["title"] == "Gadget"

    # 2. Failed execution (non-existent table)
    fail_state: AgentState = {
        "sanitized_sql": "SELECT * FROM non_existent_table",
        "target_engine": engine
    }
    fail_res = await execution_node(fail_state)
    assert fail_res["was_successful"] is False
    assert fail_res["execution_error"] is not None

@pytest.mark.asyncio
async def test_self_correction_guidance():
    state: AgentState = {
        "retry_count": 0,
        "max_retries": 2,
        "sanitized_sql": "SELECT customer_net_margin FROM customers",
        "execution_error": "no such column: customer_net_margin",
        "relevant_columns": [
            {"column_name": "id"},
            {"column_name": "name"},
            {"column_name": "city"}
        ],
        "relevant_tables": ["customers"]
    }

    correction_res = await self_correction_node(state)
    assert correction_res["retry_count"] == 1
    assert "Available columns" in correction_res["retry_hint"]
    assert "customers" in correction_res["retry_hint"]
    assert len(correction_res["retry_history"]) == 1

@pytest.mark.asyncio
async def test_result_explainer_synthesizer():
    state: AgentState = {
        "query": "What is our total revenue for 2023?",
        "query_result": [{"total_revenue": 1250000.0}],
        "was_successful": True,
        "analysis_result": {
            "trends": [],
            "outliers": []
        }
    }

    res = await result_explainer_node(state)
    assert "result_explanation" in res
    expl = res["result_explanation"].lower()
    assert any(term in expl for term in ["1,250,000", "1.25", "1250000", "million", "revenue"])

