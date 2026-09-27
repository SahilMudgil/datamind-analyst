import pytest
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import User, DatabaseConnection, SchemaCache
from agent.state import AgentState
from agent.intent_check import heuristic_intent_resolution, intent_check_node
from agent.schema_linker import schema_linker_node
from agent.sql_generator import heuristic_sql_generation, sql_generator_node
from agent.safety_validator import validate_sql_safety, safety_validator_node
from agent.graph import agent_pipeline




# --- 1. Intent Check & Disambiguation Tests ---
def test_intent_classification_cases():
    # 1. Standalone data query
    res1 = heuristic_intent_resolution("What is our total revenue for the year 2023?", history=[])
    assert res1["intent"] == "data_query"
    assert res1["is_valid_intent"] is True
    assert "total revenue" in res1["resolved_query"]

    # 2. Greeting
    res2 = heuristic_intent_resolution("Hello", history=[])
    assert res2["intent"] == "greeting"
    assert res2["is_valid_intent"] is False

    # 3. Off-topic prompt
    res3 = heuristic_intent_resolution("write a poem about flowers", history=[])
    assert res3["intent"] == "off_topic"
    assert res3["is_valid_intent"] is False

    # 4. Multi-turn Follow-up Resolution
    history = [
        {"role": "user", "content": "What is our total revenue for the year 2023?"},
        {"role": "assistant", "content": "Total revenue was $1,250,000 across 4,200 orders."}
    ]
    res4 = heuristic_intent_resolution("Now just show me Mumbai.", history=history)
    assert res4["intent"] == "conversational_followup"
    assert res4["is_valid_intent"] is True
    assert "Mumbai" in res4["resolved_query"]
    assert "revenue" in res4["resolved_query"]


# --- 2. AST Safety Validator Adversarial Tests ---
def test_safety_validator_adversarial_suite():
    allowed = {"orders", "order_items", "products", "customers", "sample"}

    # Adversarial Attack 1: DROP TABLE
    is_safe, violations, _ = validate_sql_safety("DROP TABLE users;", allowed_tables=allowed)
    assert is_safe is False
    assert any("SELECT" in v or "DROP" in v for v in violations)

    # Adversarial Attack 2: DELETE statement
    is_safe, violations, _ = validate_sql_safety("DELETE FROM products WHERE id = 1;", allowed_tables=allowed)
    assert is_safe is False

    # Adversarial Attack 3: Multi-statement SQL Injection
    is_safe, violations, _ = validate_sql_safety("SELECT * FROM products; DROP TABLE customers;", allowed_tables=allowed)
    assert is_safe is False
    assert any("Multi-statement" in v for v in violations)

    # Adversarial Attack 4: SQL Comment syntax evasion
    is_safe, violations, _ = validate_sql_safety("SELECT * FROM orders WHERE id = 1 -- secret payload", allowed_tables=allowed)
    assert is_safe is False
    assert any("comment" in v for v in violations)

    # Adversarial Attack 5: Unauthorized table access (not in allow-list)
    is_safe, violations, _ = validate_sql_safety("SELECT * FROM credit_cards;", allowed_tables=allowed)
    assert is_safe is False
    assert any("not exist in authorized schema" in v for v in violations)

    # Adversarial Attack 6: Restricted System Catalog Access
    is_safe, violations, _ = validate_sql_safety("SELECT * FROM pg_shadow;", allowed_tables=allowed)
    assert is_safe is False
    assert any("restricted or system catalog" in v or "not exist" in v for v in violations)

    # Legitimate Query 1: Auto-Inject LIMIT 100
    is_safe, violations, sanitized = validate_sql_safety("SELECT id, total_amount FROM orders", allowed_tables=allowed, max_limit=100)
    assert is_safe is True
    assert len(violations) == 0
    assert "LIMIT 100" in sanitized.upper()

    # Legitimate Query 2: Clamp excessive LIMIT
    is_safe, violations, sanitized = validate_sql_safety("SELECT id FROM orders LIMIT 50000", allowed_tables=allowed, max_limit=100)
    assert is_safe is True
    assert "LIMIT 100" in sanitized.upper()


# --- 3. Schema Linker Tests ---
@pytest.mark.asyncio
async def test_schema_linker_node(db_session):
    db = db_session
    # Create test connection
    user = User(email="linker_test@example.com", password_hash="hash")
    db.add(user)
    db.commit()

    conn = DatabaseConnection(user_id=user.id, display_name="Test Store", db_type="postgresql")
    db.add(conn)
    db.commit()

    # Seed schema cache entries
    sc1 = SchemaCache(connection_id=conn.id, table_name="orders", column_name="total_amount", data_type="NUMERIC", ai_description="Total revenue amount")
    sc2 = SchemaCache(connection_id=conn.id, table_name="orders", column_name="id", data_type="INTEGER", is_primary_key=True, ai_description="Order ID")
    sc3 = SchemaCache(connection_id=conn.id, table_name="customers", column_name="city", data_type="VARCHAR", ai_description="Customer city location")
    db.add_all([sc1, sc2, sc3])
    db.commit()

    state: AgentState = {
        "query": "What is our total revenue for 2023?",
        "resolved_query": "What is our total revenue for 2023?",
        "connection_id": conn.id,
        "is_valid_intent": True,
        "trace_steps": []
    }

    updated_state = await schema_linker_node(state, db=db)
    assert "orders" in updated_state["relevant_tables"]
    assert "total_amount" in updated_state["schema_prompt"]
    assert len(updated_state["trace_steps"]) == 1


# --- 4. SQL Generator Node Test ---
@pytest.mark.asyncio
async def test_sql_generator_node():
    state: AgentState = {
        "query": "What is our total revenue for the year 2023?",
        "resolved_query": "What is our total revenue for the year 2023?",
        "schema_prompt": "Table: `orders`\n  • `total_amount` (NUMERIC)\n  • `order_date` (DATE)",
        "relevant_tables": ["orders"],
        "is_valid_intent": True,
        "trace_steps": []
    }

    res = await sql_generator_node(state)
    assert res["generated_sql"] is not None
    assert res["generated_sql"].upper().startswith("SELECT")
    assert "orders" in res["generated_sql"].lower()


# --- 5. Full LangGraph End-to-End Pipeline Execution ---
@pytest.mark.asyncio
async def test_full_langgraph_pipeline_e2e(db_session):
    db = db_session
    user = User(email="e2e_agent@example.com", password_hash="hash")
    db.add(user)
    db.commit()

    conn = DatabaseConnection(user_id=user.id, display_name="Production E-commerce", db_type="postgresql")
    db.add(conn)
    db.commit()

    # Cache tables
    db.add_all([
        SchemaCache(connection_id=conn.id, table_name="orders", column_name="id", data_type="INTEGER", is_primary_key=True),
        SchemaCache(connection_id=conn.id, table_name="orders", column_name="total_amount", data_type="NUMERIC", ai_description="Total revenue"),
        SchemaCache(connection_id=conn.id, table_name="orders", column_name="order_date", data_type="DATE", ai_description="Date of purchase"),
        SchemaCache(connection_id=conn.id, table_name="orders", column_name="status", data_type="VARCHAR", ai_description="Order status completed")
    ])
    db.commit()

    # Create and seed target table in memory
    target_engine = create_engine("sqlite:///:memory:")
    with target_engine.connect() as t_conn:
        t_conn.execute(text("CREATE TABLE orders (id INT, total_amount FLOAT, order_date DATE, status TEXT);"))
        t_conn.execute(text("INSERT INTO orders VALUES (1, 1500.0, '2023-05-01', 'completed'), (2, 2500.0, '2023-08-15', 'completed');"))
        t_conn.commit()

    initial_state: AgentState = {
        "query": "What is our total revenue for the year 2023?",
        "connection_id": conn.id,
        "conversation_history": [],
        "max_retries": 2,
        "retry_count": 0,
        "trace_steps": [],
        "db": db,
        "target_engine": target_engine
    }

    # Execute compiled LangGraph pipeline
    final_state = await agent_pipeline.ainvoke(initial_state)

    # Assertions on pipeline output
    assert final_state["intent"] == "data_query"
    assert final_state["is_valid_intent"] is True
    assert len(final_state["relevant_tables"]) >= 1
    assert "orders" in final_state["relevant_tables"]
    assert final_state["generated_sql"] is not None
    assert final_state["is_safe"] is True
    assert final_state["sanitized_sql"] is not None
    assert "LIMIT" in final_state["sanitized_sql"].upper()

    # Verify trace steps were recorded through all 7 nodes
    step_names = [s["step_name"] for s in final_state["trace_steps"]]
    assert any("Intent" in name for name in step_names)
    assert any("Schema" in name for name in step_names)
    assert any("SQL Generation" in name for name in step_names)
    assert any("Safety Validation" in name for name in step_names)
    assert any("Database Execution" in name for name in step_names)
    assert any("Data Analysis" in name for name in step_names)
    assert any("Result Explanation" in name for name in step_names)

    # Verify execution, chart, and explanation outputs
    assert final_state["was_successful"] is True
    assert final_state["query_result"] is not None
    assert len(final_state["query_result"]) == 1
    assert final_state["chart_type"] == "stat_card"
    assert final_state["chart_config"]["format"] == "currency"
    assert final_state["result_explanation"] is not None
    assert "$4,000" in final_state["result_explanation"]

    db.close()


# --- 6. Self-Correction Reflection Test ---
@pytest.mark.asyncio
async def test_self_correction_reflection():
    from agent.self_correction import self_correction_node, analyze_database_error

    # Test error analysis for missing column
    hint1 = analyze_database_error(
        error_msg='column "net_margin" does not exist',
        previous_sql="SELECT net_margin FROM orders",
        schema_prompt="Table: `orders`\n• `total_amount` (NUMERIC)"
    )
    assert "net_margin" in hint1
    assert "does not exist" in hint1

    # Test error analysis for GROUP BY
    hint2 = analyze_database_error(
        error_msg="column orders.customer_id must appear in the GROUP BY clause or be used in an aggregate function",
        previous_sql="SELECT customer_id, SUM(total_amount) FROM orders",
        schema_prompt=""
    )
    assert "GROUP BY" in hint2

    # Test self-correction node state mutation
    mock_state: AgentState = {
        "generated_sql": "SELECT non_existent_col FROM orders;",
        "execution_error": 'no such column: non_existent_col',
        "retry_count": 0,
        "max_retries": 2,
        "retry_history": [],
        "trace_steps": []
    }

    corrected_state = await self_correction_node(mock_state)
    assert corrected_state["retry_count"] == 1
    assert corrected_state["retry_hint"] is not None
    assert len(corrected_state["retry_history"]) == 1
    assert corrected_state["retry_history"][0]["attempt"] == 1
    assert len(corrected_state["trace_steps"]) == 1


# --- 7. Data Analysis: Trends, Outliers, & Chart Selection Test ---
@pytest.mark.asyncio
async def test_data_analysis_and_chart_selection():
    from agent.data_analysis import data_analysis_node

    # Test 1: Trend calculation and Line chart selection
    time_series_rows = [
        {"order_month": "2023-01", "monthly_revenue": 10000},
        {"order_month": "2023-02", "monthly_revenue": 12000},
        {"order_month": "2023-03", "monthly_revenue": 15000},
        {"order_month": "2023-04", "monthly_revenue": 14000},
        {"order_month": "2023-05", "monthly_revenue": 85000} # deliberate outlier
    ]

    state: AgentState = {
        "query_result": time_series_rows,
        "column_names": ["order_month", "monthly_revenue"],
        "trace_steps": []
    }

    analyzed = await data_analysis_node(state)
    assert analyzed["chart_type"] == "line"
    assert "trends" in analyzed["analysis_result"]
    assert len(analyzed["analysis_result"]["trends"]) >= 1

    # Check that outlier is detected via z-score
    outliers = analyzed["analysis_result"]["outliers"]
    assert len(outliers) >= 1
    assert any(o["value"] == 85000 for o in outliers)

    # Test 2: Categorical ranking Bar chart
    cat_rows = [
        {"category": "Electronics", "total_sales": 50000},
        {"category": "Home", "total_sales": 30000},
        {"category": "Apparel", "total_sales": 20000}
    ]
    bar_state = await data_analysis_node({
        "query_result": cat_rows,
        "column_names": ["category", "total_sales"],
        "trace_steps": []
    })
    assert bar_state["chart_type"] == "bar"
    assert bar_state["chart_config"]["xAxis"] == "category"
    assert bar_state["chart_config"]["yAxis"] == "total_sales"


# --- 8. Result Explainer Node Test ---
@pytest.mark.asyncio
async def test_result_explainer_node():
    from agent.result_explainer import result_explainer_node

    state: AgentState = {
        "query": "What is our total revenue for 2023?",
        "resolved_query": "What is our total revenue for 2023?",
        "query_result": [{"total_revenue": 45000.0}],
        "analysis_result": {"summary": {"total_revenue": {"total": 45000.0}}},
        "chart_type": "stat_card",
        "was_successful": True,
        "trace_steps": []
    }

    explained = await result_explainer_node(state)
    assert explained["result_explanation"] is not None
    assert "$45,000" in explained["result_explanation"]
    assert len(explained["trace_steps"]) == 1


# --- 9. Full Chat REST API Integration Test ---
def test_chat_rest_api_flow(client):

    # 1. Register user
    reg = client.post(
        "/api/auth/register",
        json={"email": "chat_tester@example.com", "password": "password123", "name": "Chat Analyst"}
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create sample CSV upload to query against
    csv_bytes = b"transaction_id,category,total_revenue,city\n1,Electronics,45000,Mumbai\n2,Home,12000,Delhi\n"
    up_res = client.post(
        "/api/csv/upload",
        files={"file": ("sales.csv", csv_bytes, "text/csv")},
        data={"display_name": "Sales CSV Dataset"},
        headers=headers
    )
    assert up_res.status_code == 201
    conn_id = up_res.json()["connection_id"]

    # 3. Create conversation session
    conv_res = client.post(
        "/api/chat/conversations",
        json={"connection_id": conn_id, "title": "Sales Analysis Session"},
        headers=headers
    )
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    # 4. Post query via REST API
    query_res = client.post(
        "/api/chat/query",
        json={
            "connection_id": conn_id,
            "conversation_id": conv_id,
            "query": "Which top 5 product categories generated the most sales?"
        },
        headers=headers
    )
    assert query_res.status_code == 200
    q_data = query_res.json()
    assert q_data["role"] == "assistant"
    assert q_data["was_successful"] is True
    assert q_data["final_sql"] is not None
    assert q_data["query_result"] is not None
    assert q_data["chart_type"] in ["bar", "stat_card"]
    assert q_data["content"] is not None

    # 5. Fetch conversation messages
    msgs_res = client.get(f"/api/chat/conversations/{conv_id}/messages", headers=headers)
    assert msgs_res.status_code == 200
    msgs = msgs_res.json()
    assert len(msgs) == 2 # 1 user + 1 assistant
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


