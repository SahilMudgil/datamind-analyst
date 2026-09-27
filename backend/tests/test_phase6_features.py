import pytest
from datetime import datetime
from sqlalchemy import text
from models.models import User, DatabaseConnection, Conversation, Message, QueryCache, DashboardWidget, Bookmark
from services.query_cache_service import query_cache_service
from services.llm_tracking_service import llm_tracking_service
from agent.intent_check import heuristic_intent_resolution
from evaluation.benchmark_runner import run_benchmark_suite


@pytest.mark.asyncio
async def test_semantic_query_caching_flow(db_session):
    # Setup connection
    user = User(email="cache_test_user@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    conn = DatabaseConnection(user_id=user.id, display_name="Cache DB", db_type="sqlite")
    db_session.add(conn)
    db_session.commit()

    # 1. Miss initially
    miss = await query_cache_service.find_cached_query(
        connection_id=conn.id,
        question_text="What was our total revenue in 2023?",
        db=db_session
    )
    assert miss is None

    # 2. Save into cache
    cached = await query_cache_service.save_cached_query(
        connection_id=conn.id,
        question_text="What was our total revenue in 2023?",
        generated_sql="SELECT SUM(total_amount) FROM orders WHERE order_date >= '2023-01-01';",
        db=db_session
    )
    assert cached is not None
    assert cached.hit_count == 1

    # 3. Hit on identical question
    hit = await query_cache_service.find_cached_query(
        connection_id=conn.id,
        question_text="What was our total revenue in 2023?",
        db=db_session
    )
    assert hit is not None
    assert hit.generated_sql == "SELECT SUM(total_amount) FROM orders WHERE order_date >= '2023-01-01';"
    assert hit.hit_count >= 2


def test_conversational_memory_followup_resolution():
    history = [
        {"role": "user", "content": "What is our total revenue for the year 2023?"},
        {"role": "assistant", "content": "The total revenue for 2023 is ₹4,000."}
    ]

    # Test 1: Geographic drilldown follow-up
    res1 = heuristic_intent_resolution("Now just show me Mumbai.", history=history)
    assert res1["intent"] == "conversational_followup"
    assert "Mumbai" in res1["resolved_query"]
    assert "2023" in res1["resolved_query"]

    # Test 2: Pronoun context resolution
    res2 = heuristic_intent_resolution("What were their highest sales?", history=history)
    assert res2["intent"] == "conversational_followup"
    assert "previous question" in res2["resolved_query"] or "context" in res2["intent_explanation"]


def test_dashboard_widgets_and_bookmarks_api_flow(client, db_session):
    # 1. Register test user
    reg = client.post(
        "/api/auth/register",
        json={"email": "dashboard_user@example.com", "password": "securepassword123"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user = db_session.query(User).filter(User.email == "dashboard_user@example.com").first()

    # 2. Seed connection & message
    conn = DatabaseConnection(user_id=user.id, display_name="Sales DB", db_type="sqlite")
    db_session.add(conn)
    db_session.commit()

    conv = Conversation(user_id=user.id, connection_id=conn.id, title="Revenue Review")
    db_session.add(conv)
    db_session.commit()

    msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content="Revenue was ₹500,000 across categories.",
        final_sql="SELECT category, SUM(revenue) FROM sales GROUP BY category;",
        chart_type="bar",
        chart_config={"xAxis": "category", "yAxis": "revenue"}
    )
    db_session.add(msg)
    db_session.commit()

    # 3. Create Dashboard Widget
    widget_payload = {
        "connection_id": conn.id,
        "title": "Category Revenue Breakdown",
        "sql_query": msg.final_sql,
        "chart_type": "bar",
        "chart_config": msg.chart_config,
        "width": 2,
        "height": 1
    }
    w_res = client.post("/api/dashboard/widgets", headers=headers, json=widget_payload)
    assert w_res.status_code == 201
    w_data = w_res.json()
    assert w_data["title"] == "Category Revenue Breakdown"
    widget_id = w_data["id"]

    # 4. List Widgets
    list_w = client.get("/api/dashboard/widgets", headers=headers)
    assert list_w.status_code == 200
    assert len(list_w.json()) >= 1

    # 5. Delete Widget
    del_w = client.delete(f"/api/dashboard/widgets/{widget_id}", headers=headers)
    assert del_w.status_code == 204

    # 6. Create Bookmark
    bm_res = client.post(
        "/api/bookmarks",
        headers=headers,
        json={"message_id": msg.id, "label": "Key Sales Metric", "folder": "Executive"}
    )
    assert bm_res.status_code == 201
    bm_data = bm_res.json()
    assert bm_data["label"] == "Key Sales Metric"
    bm_id = bm_data["id"]

    # 7. List Bookmarks
    list_bm = client.get("/api/bookmarks", headers=headers)
    assert list_bm.status_code == 200
    assert len(list_bm.json()) >= 1

    # 8. Delete Bookmark
    del_bm = client.delete(f"/api/bookmarks/{bm_id}", headers=headers)
    assert del_bm.status_code == 204


def test_llm_usage_and_analytics_api_flow(client, db_session):
    reg = client.post(
        "/api/auth/register",
        json={"email": "analytics_user@example.com", "password": "securepassword123"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user = db_session.query(User).filter(User.email == "analytics_user@example.com").first()

    # Log usage via tracking service
    llm_tracking_service.log_usage(
        db=db_session,
        user_id=user.id,
        provider="gemini",
        model_used="gemini-2.5-flash",
        step_type="sql_generation",
        input_tokens=250,
        output_tokens=75,
        latency_ms=180
    )

    # Query Analytics API
    res = client.get("/api/analytics/llm-usage", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_calls"] >= 1
    assert data["total_tokens"] >= 325
    assert data["total_cost_usd"] > 0

    # Query Cache Stats API
    c_res = client.get("/api/analytics/cache-stats", headers=headers)
    assert c_res.status_code == 200
    assert "total_cached_queries" in c_res.json()


@pytest.mark.asyncio
async def test_full_benchmark_suite_evaluation():
    report = await run_benchmark_suite()
    assert report["total_queries"] == 6
    assert report["passed_queries"] == 6
    assert report["pass_rate_pct"] == 100.0
