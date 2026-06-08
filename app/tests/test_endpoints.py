import io
import pytest

from fastapi.testclient import TestClient
from app.chain.steps import LLMRunnerOutput
from app.main import app
from app.data import clear_dataset
from unittest.mock import patch
from app.schemas import AskResponse
from app.config import settings

client = TestClient(app)

content = "col1,col2\n1,2\n3,4\n"

def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    
def test_health_returns_correct_body():
    response = client.get("/health")
    assert response.json() == {"status": "ok"}
    
def test_upload_csv():
    response = client.post("/data/upload", files={"file": ("test.csv", io.BytesIO(content.encode()), "text/csv")})
    assert response.status_code == 200
    data = response.json()
    assert data["rows"] == 2
    assert "columns" in data
    assert "dtypes" in data

@pytest.fixture(autouse=True)
def reset_dataset():
    clear_dataset()
    yield

def test_stats_no_dataset():
    response = client.get("/data/stats")
    assert response.status_code == 404
    
def test_stats_after_upload():
    client.post("/data/upload", files={"file": ("test.csv", io.BytesIO(content.encode()), "text/csv")})
    response = client.get("/data/stats")
    assert response.status_code == 200
    assert "col1" in response.json()

def test_ask_no_dataset():
    response = client.post("/ai/ask", json={"question": "test"})
    assert response.status_code == 400

def test_ask_with_mocked_llm():
    client.post("/data/upload", files={"file": ("test.csv", io.BytesIO(content.encode()), "text/csv")})
    fake = LLMRunnerOutput(raw_text="42", question="test")
    with patch("app.chain.steps.LLMRunner.invoke", return_value=fake):
        response = client.post("/ai/ask", json={"question": "test"})
    assert response.status_code == 200
    assert "answer" in response.json()
    assert "model" in response.json()

def test_ask_model_failure_returns_500():
    client.post("/data/upload", files={"file": ("test.csv", io.BytesIO(content.encode()), "text/csv")})
    with patch("app.chain.steps.LLMRunner.invoke", side_effect=RuntimeError("Model timed out")):
        response = client.post("/ai/ask", json={"question": "test"})
    assert response.status_code == 500
