from pathlib import Path

from fastapi.testclient import TestClient

from admin.app import app
from data.base import Base
from data.db import get_db_session
from data.db import get_engine
from data.db import get_session_factory
from data.models import Provider
from data.models import RecordedRequest
from data.models import RecordedResponse


def test_records_list_route_exists(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'records.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    session = get_session_factory(database_url)()
    provider = Provider(
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
    session.add(provider)
    session.flush()
    request = RecordedRequest(
        provider_id=provider.id,
        request_type="chat_completions",
        model="gpt-4o-mini",
        is_stream=False,
        request_headers_json={},
        request_body_json={"messages": []},
        request_text_snapshot="{}",
    )
    session.add(request)
    session.flush()
    session.add(
        RecordedResponse(
            request_id=request.id,
            http_status=200,
            response_headers_json={},
            response_body_json={"id": "resp-1"},
            response_text_snapshot="{}",
        )
    )
    session.commit()
    session.close()

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    list_response = client.get("/admin/records")
    detail_response = client.get("/admin/records/1")

    app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1
    assert detail_response.status_code == 200
