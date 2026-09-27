import pytest

def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

def test_register_and_login_flow(client):
    # 1. Register new user
    reg_response = client.post(
        "/api/auth/register",
        json={"email": "analyst@example.com", "password": "securepassword123", "name": "Lead Analyst"}
    )
    assert reg_response.status_code == 201
    reg_data = reg_response.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == "analyst@example.com"
    assert reg_data["user"]["name"] == "Lead Analyst"

    token = reg_data["access_token"]

    # 2. Duplicate registration should fail
    dup_response = client.post(
        "/api/auth/register",
        json={"email": "analyst@example.com", "password": "anotherpassword", "name": "Duplicate"}
    )
    assert dup_response.status_code == 400

    # 3. Login with correct credentials
    login_response = client.post(
        "/api/auth/login",
        json={"email": "analyst@example.com", "password": "securepassword123"}
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data

    # 4. Login with wrong password
    bad_login = client.post(
        "/api/auth/login",
        json={"email": "analyst@example.com", "password": "wrongpassword"}
    )
    assert bad_login.status_code == 401

    # 5. Get current user profile with Bearer token
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "analyst@example.com"

    # 6. Access /me without token should be 401
    no_token_response = client.get("/api/auth/me")
    assert no_token_response.status_code == 401
