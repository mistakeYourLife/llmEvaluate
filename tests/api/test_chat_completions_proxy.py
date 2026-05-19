from fastapi.testclient import TestClient

from api.app import app


def test_chat_completions_route_exists():
    client = TestClient(app)
    response = client.post("/v1/chat/completions", json={"model": "test", "messages": []})
    assert response.status_code != 404
