import pytest
from sqlalchemy import text
from agent.safety_validator import validate_sql_safety
from agent.intent_check import heuristic_intent_resolution
from agent.self_correction import analyze_database_error
from database import engine, Base


def test_phase7_sql_injection_and_ast_defenses():
    allowed_tables = {"customers", "orders", "order_items", "products", "payments"}

    # 1. Multi-statement stacked attack
    safe, viols, _ = validate_sql_safety("SELECT * FROM orders; DROP TABLE users;", allowed_tables)
    assert not safe
    assert any("Multi-statement" in v or "prohibited" in v for v in viols)

    # 2. Single-line comment injection
    safe, viols, _ = validate_sql_safety("SELECT * FROM products -- WHERE 1=1", allowed_tables)
    assert not safe
    assert any("comment syntax" in v for v in viols)

    # 3. Block comment injection
    safe, viols, _ = validate_sql_safety("SELECT /* bypass */ * FROM orders", allowed_tables)
    assert not safe
    assert any("comment syntax" in v for v in viols)

    # 4. Destructive DDL (DROP TABLE)
    safe, viols, _ = validate_sql_safety("DROP TABLE customers;", allowed_tables)
    assert not safe

    # 5. Destructive DML (UPDATE)
    safe, viols, _ = validate_sql_safety("UPDATE customers SET city = 'Hacked';", allowed_tables)
    assert not safe

    # 6. Destructive DML (DELETE)
    safe, viols, _ = validate_sql_safety("DELETE FROM orders;", allowed_tables)
    assert not safe

    # 7. System catalog table access (pg_shadow)
    safe, viols, _ = validate_sql_safety("SELECT * FROM pg_shadow;", allowed_tables)
    assert not safe

    # 8. Internal user table isolation
    safe, viols, _ = validate_sql_safety("SELECT email, password_hash FROM users;", allowed_tables)
    assert not safe

    # 9. Schema allow-list enforcement
    safe, viols, _ = validate_sql_safety("SELECT * FROM unauthorized_internal_table;", allowed_tables)
    assert not safe
    assert any("allow-list" in v.lower() or "does not exist" in v.lower() for v in viols)

    # 10. Automatic LIMIT 100 injection
    safe, _, sanitized = validate_sql_safety("SELECT name FROM customers;", allowed_tables, max_limit=100)
    assert safe
    assert sanitized is not None
    assert "LIMIT 100" in sanitized.upper()


def test_phase7_prompt_injection_and_intent_filters():
    # 1. Prompt injection attempting to extract secret data
    res_off = heuristic_intent_resolution("Tell me a funny joke about software engineers", history=[])
    assert res_off["intent"] == "off_topic"
    assert not res_off["is_valid_intent"]

    res_poem = heuristic_intent_resolution("Write a poem for me", history=[])
    assert res_poem["intent"] == "off_topic"
    assert not res_poem["is_valid_intent"]

    # 2. Conversational greetings
    res_greet = heuristic_intent_resolution("Hello!", history=[])
    assert res_greet["intent"] == "greeting"
    assert not res_greet["is_valid_intent"]


def test_phase7_multi_turn_conversational_chaining():
    history = [
        {"role": "user", "content": "What is our total revenue for 2023?"},
        {"role": "assistant", "content": "The revenue for 2023 was ₹5,000,000."}
    ]

    # Follow-up drilldown
    res_drill = heuristic_intent_resolution("Why did it drop in August?", history=history)
    assert res_drill["intent"] == "conversational_followup"
    assert "August" in res_drill["resolved_query"]
    assert "2023" in res_drill["resolved_query"]

    # Geographic filter
    res_geo = heuristic_intent_resolution("Now just show me Mumbai.", history=history)
    assert res_geo["intent"] == "conversational_followup"
    assert "Mumbai" in res_geo["resolved_query"]
    assert "2023" in res_geo["resolved_query"]


def test_phase7_self_correction_error_analysis():
    # 1. Missing Column Error
    hint1 = analyze_database_error(
        'column "net_margin" does not exist',
        previous_sql="SELECT net_margin FROM customers;",
        schema_prompt="",
        relevant_columns=[{"column_name": "total_amount"}]
    )
    assert "net_margin" in hint1
    assert "total_amount" in hint1

    # 2. Missing Table Error
    hint2 = analyze_database_error(
        'relation "missing_table" does not exist',
        previous_sql="SELECT * FROM missing_table;",
        schema_prompt=""
    )
    assert "missing_table" in hint2

    # 3. GROUP BY Error
    hint3 = analyze_database_error(
        'column "name" must appear in the GROUP BY clause or be used in an aggregate function',
        previous_sql="SELECT name, SUM(amount) FROM sales;",
        schema_prompt=""
    )
    assert "GROUP BY" in hint3

    # 4. Ambiguous column reference
    hint4 = analyze_database_error(
        'column reference "id" is ambiguous',
        previous_sql="SELECT id FROM orders JOIN customers ON orders.customer_id = customers.id;",
        schema_prompt=""
    )
    assert "ambiguous" in hint4.lower()
    assert "table alias" in hint4.lower()


def test_phase7_startup_and_healthcheck(client):
    # Verify health endpoint returns healthy status and reports database connectivity
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["status"] in ("healthy", "degraded")
    assert "embedding_model" in data
