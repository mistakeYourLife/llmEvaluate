from pathlib import Path

from fastapi.testclient import TestClient

from admin.app import app
from data.base import Base
from data.db import get_db_session
from data.db import get_engine
from api.providers.base import ProviderProbeResult


class FakeAdapter:
    def probe(self):
        return ProviderProbeResult(ok=True, detail="reachable")


def test_provider_test_endpoint_returns_result(tmp_path: Path, monkeypatch):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'providers-test.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    def override_db_session():
        yield from get_db_session(database_url)

    monkeypatch.setattr("admin.routes.providers.build_provider_adapter", lambda provider: FakeAdapter())
    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    create_response = client.post(
        "/admin/providers",
        json={
            "name": "OpenAI",
            "code": "openai",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "secret",
            "default_model": "gpt-4o-mini",
        },
    )
    provider_id = create_response.json()["id"]

    response = client.post(f"/admin/providers/{provider_id}/test")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ok"] is True
