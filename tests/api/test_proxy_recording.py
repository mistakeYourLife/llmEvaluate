from pathlib import Path

from fastapi.testclient import TestClient

from api.app import app
from api.providers.base import ProviderChatCompletionResult
from data.base import Base
from data.db import get_db_session
from data.db import get_engine
from data.db import get_session_factory
from data.models import Provider
from data.models import RecordedRequest
from data.models import RecordedResponse


class FakeChatAdapter:
    def __init__(self):
        self.calls: list[tuple[dict, str | None]] = []

    def chat_completions(self, payload: dict, model: str | None = None) -> ProviderChatCompletionResult:
        self.calls.append((payload, model))
        return ProviderChatCompletionResult(
            status_code=200,
            body={
                "id": "chatcmpl-real",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "real-response"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
            headers={"content-type": "application/json"},
            first_token_latency_ms=12,
            complete_latency_ms=30,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            tokens_per_second=166.67,
            output_text="real-response",
        )


def test_proxy_persists_recording_without_breaking_response(tmp_path: Path, monkeypatch):
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

    adapter = FakeChatAdapter()
    monkeypatch.setattr("api.services.proxy_service.build_provider_adapter", lambda provider: adapter)
    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    response = client.post("/v1/chat/completions", json={"messages": []})

    session = get_session_factory(database_url)()
    try:
        request_count = session.query(RecordedRequest).count()
        response_count = session.query(RecordedResponse).count()
        stored_request = session.query(RecordedRequest).one()
        stored_response = session.query(RecordedResponse).one()
    finally:
        session.close()

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == "chatcmpl-real"
    assert adapter.calls[0][1] == "gpt-4o-mini"
    assert request_count == 1
    assert response_count == 1
    assert stored_request.request_body_json["model"] == "gpt-4o-mini"
    assert stored_response.total_tokens == 15
