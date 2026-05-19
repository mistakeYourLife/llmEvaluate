from pathlib import Path

from fastapi.testclient import TestClient

from api.app import app
from data.base import Base
from data.db import get_db_session
from data.db import get_engine
from data.db import get_session_factory
from data.models import Provider
from data.models import RecordedRequest
from data.models import RecordedResponse


def test_proxy_persists_recording_without_breaking_response(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'proxy-recording.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    seed_session = get_session_factory(database_url)()
    seed_session.add(
        Provider(
            name="OpenAI",
            code="openai",
            provider_type="openai",
            base_url="https://api.openai.com/v1",
            api_key_encrypted="plain:secret",
            default_model="gpt-4o-mini",
            enabled=True,
            timeout_ms=30000,
            max_retries=1,
            extra_config_json={},
        )
    )
    seed_session.commit()
    seed_session.close()

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    response = client.post("/v1/chat/completions", json={"model": "test", "messages": []})

    session = get_session_factory(database_url)()
    try:
        request_count = session.query(RecordedRequest).count()
        response_count = session.query(RecordedResponse).count()
    finally:
        session.close()

    app.dependency_overrides.clear()

    assert response.status_code in (200, 400, 502)
    assert request_count == 1
    assert response_count == 1
