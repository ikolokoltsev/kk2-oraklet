from fastapi.testclient import TestClient
from app.main import app
import io

client = TestClient(app)

content = "col1,col2\n1,2\n3,4\n"
file = io.BytesIO(content.encode())

def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    
def test_health_returns_correct_body():
    response = client.get("/health")
    assert response.json() == {"status": "ok"}
    
def test_upload_csv():
    response = client.post("/data/upload", files={"file": ("test.csv", file, "text/csv")})
    assert response.status_code == 200
    data = response.json()
    assert data["rows"] == 2
    assert "columns" in data
    assert "dtypes" in data