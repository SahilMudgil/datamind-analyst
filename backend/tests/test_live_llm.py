import pytest
import asyncio
from services.embedding_service import embedding_service
from agent.intent_check import intent_check_node
from agent.result_explainer import result_explainer_node
from agent.sql_generator import sql_generator_node
from config import settings


@pytest.mark.asyncio
async def test_live_gemini_embedding_generation():
    """Verify live Gemini embedding generation produces 768-dim vectors."""
    text = "customer order revenue and product items"
    emb = await embedding_service.get_embedding(text)
    assert isinstance(emb, list)
    assert len(emb) == 768
    assert all(isinstance(x, (float, int)) for x in emb)


@pytest.mark.asyncio
async def test_live_groq_intent_classification():
    """Verify live Groq query intent classification."""
    state = {
        "query": "Show me the top 10 best-selling products by quantity",
        "conversation_history": []
    }
    result = await intent_check_node(state)
    assert result["intent"] in ("data_query", "conversational_followup")
    assert result["is_valid_intent"] is True
    assert "top 10" in result["resolved_query"].lower() or "product" in result["resolved_query"].lower()


@pytest.mark.asyncio
async def test_live_groq_result_explanation():
    """Verify live Groq generates executive business summaries."""
    state = {
        "query": "What are our sales by category?",
        "resolved_query": "What are our sales by category?",
        "query_result": [
            {"category": "Electronics", "sales": 500000},
            {"category": "Apparel", "sales": 200000}
        ],
        "analysis_result": {
            "summary": {"row_count": 2, "max_val": 500000}
        },
        "chart_type": "bar",
        "was_successful": True
    }
    result = await result_explainer_node(state)
    explanation = result.get("result_explanation")
    assert explanation is not None
    assert len(explanation) > 15
    assert "Electronics" in explanation or "500,000" in explanation or "sales" in explanation.lower()


@pytest.mark.asyncio
async def test_live_gemini_sql_generation():
    """Verify live Gemini generates valid SQL strictly using the schema."""
    schema = (
        "Table: `products` (Columns: id INTEGER, name TEXT, category TEXT, price REAL)\n"
        "Table: `orders` (Columns: id INTEGER, customer_id INTEGER, total_amount REAL, order_date DATE)"
    )
    state = {
        "query": "What is the total revenue from orders in 2023?",
        "resolved_query": "What is the total revenue from orders in 2023?",
        "schema_prompt": schema,
        "is_valid_intent": True
    }
    result = await sql_generator_node(state)
    sql = result.get("generated_sql")
    assert sql is not None
    assert "SELECT" in sql.upper()
    assert "ORDERS" in sql.upper()
    assert "TOTAL_AMOUNT" in sql.upper()
