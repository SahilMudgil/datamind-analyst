import os
import pytest
from services.encryption_service import encrypt_credential, decrypt_credential
from services.embedding_service import embedding_service
from services.csv_service import csv_service, sanitize_identifier
from services.schema_service import schema_service, generate_heuristic_description
from models.models import User, DatabaseConnection, SchemaCache

def test_credential_encryption():
    raw_pass = "readonly_secret_password_123"
    encrypted = encrypt_credential(raw_pass)
    assert encrypted != raw_pass
    assert len(encrypted) > 20
    decrypted = decrypt_credential(encrypted)
    assert decrypted == raw_pass
    assert decrypt_credential("") == ""

@pytest.mark.asyncio
async def test_embedding_generation():
    emb = await embedding_service.get_embedding("orders total_amount: Monetary value of orders.")
    assert isinstance(emb, list)
    assert len(emb) == 768
    import numpy as np
    norm = np.linalg.norm(emb)
    assert 0.95 <= norm <= 1.05

def test_csv_identifier_sanitization():
    assert sanitize_identifier("Total Revenue (INR)") == "total_revenue_inr"
    assert sanitize_identifier("1st Quarter Sales") == "t_1st_quarter_sales"
    assert sanitize_identifier("  customer - name  ") == "customer_name"

def test_ai_description_generation():
    desc_tbl = generate_heuristic_description("customers", "email", "VARCHAR(150)")
    assert "email" in desc_tbl.lower() or "customer" in desc_tbl.lower()
    
    desc_col = generate_heuristic_description("orders", "total_amount", "DECIMAL(12,2)")
    assert "total" in desc_col.lower() or "amount" in desc_col.lower()

def test_connection_and_schema_api_flow(client, db_session):
    # 1. Register test user to get token
    reg = client.post(
        "/api/auth/register",
        json={"email": "schema_tester@example.com", "password": "securepassword123"}
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test connection listing (should be empty initially)
    conns_res = client.get("/api/connections", headers=headers)
    assert conns_res.status_code == 200
    assert len(conns_res.json()) == 0

    # 3. Insert a mock connection directly to test get_connection_schema
    user = db_session.query(User).filter(User.email == "schema_tester@example.com").first()
    mock_conn = DatabaseConnection(
        user_id=user.id,
        display_name="Test Postgres",
        db_type="postgresql",
        host="localhost",
        port=5432,
        db_name="ecommerce_db",
        username="readonly_agent",
        password_encrypted=encrypt_credential("secret")
    )
    db_session.add(mock_conn)
    db_session.commit()
    db_session.refresh(mock_conn)

    # Add mock schema cache rows
    sc1 = SchemaCache(
        connection_id=mock_conn.id,
        table_name="customers",
        column_name="id",
        data_type="INTEGER",
        is_primary_key=True,
        ai_description="Unique customer ID"
    )
    sc2 = SchemaCache(
        connection_id=mock_conn.id,
        table_name="customers",
        column_name="city",
        data_type="VARCHAR(100)",
        is_primary_key=False,
        ai_description="Customer city location"
    )
    db_session.add_all([sc1, sc2])
    db_session.commit()

    # 4. Fetch schema tree via API
    schema_res = client.get(f"/api/connections/{mock_conn.id}/schema", headers=headers)
    assert schema_res.status_code == 200
    schema_data = schema_res.json()
    assert "tables" in schema_data
    assert len(schema_data["tables"]) == 1
    assert schema_data["tables"][0]["name"] == "customers"
    assert len(schema_data["tables"][0]["columns"]) == 2
    assert schema_data["tables"][0]["columns"][0]["name"] == "id"
    assert schema_data["tables"][0]["columns"][0]["is_primary_key"] is True
    assert schema_data["tables"][0]["columns"][1]["name"] == "city"

def test_csv_upload_api_flow(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "csv_user@example.com", "password": "password123"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload sample CSV
    csv_content = b"customer_id,customer_name,city,revenue\n1,Alice,Mumbai,5000\n2,Bob,Delhi,7500\n"
    files = {"file": ("sales_data.csv", csv_content, "text/csv")}
    data = {"custom_table_name": "test_sales"}

    res = client.post("/api/csv/upload", headers=headers, files=files, data=data)
    assert res.status_code == 201
    res_data = res.json()
    assert res_data["success"] is True
    assert res_data["row_count"] == 2
    assert res_data["column_count"] == 4
    assert res_data["table_name"] == "test_sales"

def test_real_sample_csv_file_import(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "sample_file_user@example.com", "password": "password123"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sample_csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sample_data", "sample.csv")
    with open(sample_csv_path, "rb") as f:
        file_bytes = f.read()

    files = {"file": ("sample.csv", file_bytes, "text/csv")}
    res = client.post("/api/csv/upload", headers=headers, files=files)
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert data["row_count"] == 14
    assert data["column_count"] == 9
    assert data["table_name"] == "sample"
    assert "total_revenue" in data["columns"]

    # Verify schema can be retrieved
    schema_res = client.get(f"/api/connections/{data['connection_id']}/schema", headers=headers)
    assert schema_res.status_code == 200
    schema_data = schema_res.json()
    assert len(schema_data["tables"]) == 1
    sample_table = schema_data["tables"][0]
    assert sample_table["name"] == "sample"
    assert len(sample_table["columns"]) == 9

