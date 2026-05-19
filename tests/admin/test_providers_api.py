from pathlib import Path

from fastapi.testclient import TestClient

from admin.app import app
from data.base import Base
from data.db import get_db_session
from data.db import get_engine


def test_create_provider(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'providers.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    response = client.post(
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

    app.dependency_overrides.clear()

    assert response.status_code == 201


def test_update_and_disable_provider(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'providers-update.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    def override_db_session():
        yield from get_db_session(database_url)

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

    update_response = client.put(
        f"/admin/providers/{provider_id}",
        json={
            "name": "OpenAI Updated",
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4.1-mini",
        },
    )
    disable_response = client.post(f"/admin/providers/{provider_id}/disable")

    app.dependency_overrides.clear()

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "OpenAI Updated"
    assert disable_response.status_code == 200
    assert disable_response.json()["enabled"] is False
