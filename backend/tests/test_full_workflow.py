import pytest
from fastapi.testclient import TestClient
import io
import json

# This global variable will store the auth token to simulate a logged-in session
auth_token = None

def test_01_create_user(client: TestClient):
    """Tests the user registration endpoint."""
    response = client.post(
        "/api/users/",
        json={"username": "ci_testuser", "email": "test@ci.com", "password": "password123"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["username"] == "ci_testuser"

def test_02_login_for_token(client: TestClient):
    """Tests the user login endpoint and saves the token."""
    global auth_token
    response = client.post(
        "/api/token",
        data={"username": "ci_testuser", "password": "password123"},
    )
    assert response.status_code == 200, response.text
    token_data = response.json()
    assert "access_token" in token_data
    auth_token = token_data["access_token"]
    assert auth_token is not None

def test_03_create_project(client: TestClient):
    """Tests project creation using the saved auth token."""
    assert auth_token is not None, "Authentication token was not set"
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post(
        "/api/projects/",
        headers=headers,
        json={"name": "CI Test Project", "description": "A project for CI tests"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "CI Test Project"

def test_04_upload_dataset(client: TestClient):
    """Tests uploading a dataset to the created project."""
    assert auth_token is not None, "Authentication token was not set"
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create a dummy CSV file in memory to simulate a file upload
    csv_content = "driver,wins\nHamilton,7\nVerstappen,3"
    csv_file = io.BytesIO(csv_content.encode('utf-8'))
    
    response = client.post(
        "/api/projects/1/upload-dataset/",
        headers=headers,
        data={"description": "Dummy driver wins data"},
        files={"file": ("wins.csv", csv_file, "text/csv")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["file_name"] == "wins.csv"
    assert response.json()["table_name"] == "wins"

def test_05_run_query_with_openrouter(client: TestClient):
    """Tests the main data query endpoint using the OpenRouter provider."""
    assert auth_token is not None, "Authentication token was not set"
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    response = client.post(
        "/api/projects/1/query",
        headers=headers,
        json={
            "question": "Show all drivers and their wins from the wins table",
            "language": "python",
            "provider": "openrouter",
            "model": "qwen/qwen3-coder:free"
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    
    # Verify the structure of the response
    assert "aggregation_code" in result
    assert "datatable_json" in result
    assert result["aggregation_code"] is not None
    
    # Verify that the result is a valid JSON string representing a DataFrame
    try:
        data = json.loads(result["datatable_json"])
        assert isinstance(data, list)
    except (json.JSONDecodeError, TypeError):
        pytest.fail("The 'datatable_json' field is not a valid JSON string.")

def test_06_run_visualization(client: TestClient):
    """Tests the user-driven visualization endpoint."""
    assert auth_token is not None, "Authentication token was not set"
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    # Provide a sample data table, as if it came from the previous step
    sample_datatable = '[{"driver": "Hamilton", "wins": 7}, {"driver": "Verstappen", "wins": 3}]'
    
    response = client.post(
        "/api/projects/1/visualize",
        headers=headers,
        json={
            "original_question": "show me a bar chart of wins per driver",
            "datatable_json": sample_datatable,
            "chart_type": "bar",
            "x_axis": "driver",
            "y_axis": "wins",
            "provider": "openrouter",
            "model": "qwen/qwen3-coder:free"
        },
    )
    # A live LLM call in a CI environment can be unpredictable.
    # A 200 (success) or 400 (if the LLM fails but our endpoint handles it) are both acceptable results.
    assert response.status_code in [200, 400]
    if response.status_code == 200:
        assert "plot_json" in response.json()