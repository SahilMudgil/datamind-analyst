import pytest
from sqlalchemy import create_engine, text
from models.models import User, DatabaseConnection, Conversation, Message, SchemaCache
from services.encryption_service import encrypt_credential

def test_chat_conversations_api_flow(client, db_session):
    # 1. Register user
    reg = client.post(
        "/api/auth/register",
        json={"email": "chat_user@example.com", "password": "securepassword123"}
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.query(User).filter(User.email == "chat_user@example.com").first()

    # 2. Create connection
    conn = DatabaseConnection(
        user_id=user.id,
        display_name="Store Analytics",
        db_type="postgresql",
        host="localhost",
        port=5432,
        db_name="ecommerce_db",
        username="readonly_agent",
        password_encrypted=encrypt_credential("secret")
    )
    db_session.add(conn)
    db_session.commit()
    db_session.refresh(conn)

    # 3. Create conversation via API
    conv_res = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={"connection_id": conn.id, "title": "Revenue Analysis 2023"}
    )
    assert conv_res.status_code == 201
    conv_data = conv_res.json()
    assert conv_data["title"] == "Revenue Analysis 2023"
    conv_id = conv_data["id"]

    # 4. List conversations
    list_res = client.get("/api/chat/conversations", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 5. Get messages (empty initially)
    msgs_res = client.get(f"/api/chat/conversations/{conv_id}/messages", headers=headers)
    assert msgs_res.status_code == 200
    assert len(msgs_res.json()) == 0

    # 6. Delete conversation
    del_res = client.delete(f"/api/chat/conversations/{conv_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["id"] == conv_id

    # Verify deleted
    list_after = client.get("/api/chat/conversations", headers=headers)
    assert not any(c["id"] == conv_id for c in list_after.json())

def test_query_rest_execution_flow(client, db_session):
    # Register user
    reg = client.post(
        "/api/auth/register",
        json={"email": "query_tester@example.com", "password": "securepassword123"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.query(User).filter(User.email == "query_tester@example.com").first()

    # Setup connection and schema cache
    conn = DatabaseConnection(
        user_id=user.id,
        display_name="Revenue DB",
        db_type="postgresql"
    )
    db_session.add(conn)
    db_session.commit()
    db_session.refresh(conn)

    db_session.add_all([
        SchemaCache(connection_id=conn.id, table_name="orders", column_name="id", data_type="INTEGER", is_primary_key=True),
        SchemaCache(connection_id=conn.id, table_name="orders", column_name="total_amount", data_type="NUMERIC", ai_description="Total revenue"),
        SchemaCache(connection_id=conn.id, table_name="orders", column_name="order_date", data_type="DATE", ai_description="Date of order")
    ])
    db_session.commit()

    # Execute greeting or query via REST
    query_res = client.post(
        "/api/chat/query",
        headers=headers,
        json={
            "connection_id": conn.id,
            "query": "Hello DataMind!"
        }
    )
    assert query_res.status_code == 200
    res_data = query_res.json()
    assert res_data["role"] == "assistant"
    assert res_data["content"] is not None
    assert res_data["conversation_id"] is not None

def test_websocket_chat_connection(client, db_session):
    reg = client.post(
        "/api/auth/register",
        json={"email": "ws_tester@example.com", "password": "securepassword123"}
    )
    token = reg.json()["access_token"]

    # Connect to WebSocket
    with client.websocket_connect(f"/api/chat/ws?token={token}") as websocket:
        init_data = websocket.receive_json()
        assert init_data["type"] == "connected"
        assert "ws_tester@example.com" in init_data["message"]
