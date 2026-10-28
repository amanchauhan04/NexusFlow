import os
os.environ["DATABASE_URL"] = "sqlite:///./test_nexusflow.db"
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
def test_health(): assert client.get("/health").json()["status"] == "ok"
def test_create_and_list_workflow():
    response = client.post("/workflows", json={"name":"test-flow","tasks":[{"id":"start","kind":"echo","payload":{"ok":True},"depends_on":[]}]})
    assert response.status_code == 201 and response.json()["name"] == "test-flow"
    assert client.get("/workflows").status_code == 200
def test_invalid_cycle_returns_422():
    response = client.post("/workflows", json={"name":"cycle","tasks":[{"id":"a","depends_on":["b"]},{"id":"b","depends_on":["a"]}]})
    assert response.status_code == 422
