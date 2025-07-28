from fastapi.testclient import TestClient

def test_read_root(client: TestClient):
    response = client.get("/api")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_and_login_user(client: TestClient):
    # Register a new user
    response = client.post(
        "/api/users/",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

    # Log in with the new user
    response = client.post(
        "/api/token",
        data={"username": "testuser", "password": "password123"},
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

def test_create_project(client: TestClient):
    # First, log in to get a token
    login_response = client.post("/api/token", data={"username": "testuser", "password": "password123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Use the token to create a project
    response = client.post(
        "/api/projects/",
        headers=headers,
        json={"name": "Test Project", "description": "A test project"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test Project"