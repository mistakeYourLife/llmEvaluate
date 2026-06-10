from api.providers.openai_compatible import OpenAICompatibleProviderAdapter
from data.models import Provider


class DummyResponse:
    def __init__(self, status_code: int, body: dict, *, text: str = "", headers: dict | None = None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {"content-type": "application/json"}
        self.text = text

    def json(self):
        return self._body


class DummyTextResponse:
    def __init__(self, status_code: int, text: str, *, headers: dict | None = None):
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/html"}
        self.text = text

    def json(self):
        raise ValueError("not json")


def test_openai_compatible_adapter_disables_proxy_env(monkeypatch):
    provider = Provider(
        id=1,
        name="Mock",
        code="mock",
        provider_type="openai",
        base_url="http://127.0.0.1:8010/v1",
        api_key_encrypted="plain:key",
        default_model="mock-model",
        enabled=True,
        timeout_ms=30000,
        max_retries=1,
        extra_config_json={},
    )
    adapter = OpenAICompatibleProviderAdapter(provider)

    post_calls = []

    def fake_post(url, **kwargs):
        post_calls.append((url, kwargs))
        return DummyResponse(
            200,
            {
                "id": "mock-chat",
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    monkeypatch.setattr("api.providers.openai_compatible.httpx.post", fake_post)

    adapter.probe()
    adapter.chat_completions({"messages": [{"role": "user", "content": "hi"}]})

    probe_url, probe_kwargs = post_calls[0]
    completion_url, completion_kwargs = post_calls[1]

    assert probe_url == "http://127.0.0.1:8010/v1/chat/completions"
    assert probe_kwargs["trust_env"] is False
    assert probe_kwargs["json"] == {
        "model": "mock-model",
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "temperature": 0,
        "stream": False,
    }

    assert completion_url == "http://127.0.0.1:8010/v1/chat/completions"
    assert completion_kwargs["trust_env"] is False


def test_openai_compatible_adapter_rejects_non_chat_completion_payload(monkeypatch):
    provider = Provider(
        id=1,
        name="Mock",
        code="mock",
        provider_type="openai",
        base_url="http://127.0.0.1:8010/v1",
        api_key_encrypted="plain:key",
        default_model="mock-model",
        enabled=True,
        timeout_ms=30000,
        max_retries=1,
        extra_config_json={},
    )
    adapter = OpenAICompatibleProviderAdapter(provider)

    html_response = DummyTextResponse(200, "<!doctype html><html><body>gateway</body></html>")
    monkeypatch.setattr("api.providers.openai_compatible.httpx.post", lambda *args, **kwargs: html_response)

    probe_result = adapter.probe()
    completion_result = adapter.chat_completions({"messages": [{"role": "user", "content": "hi"}]})

    assert probe_result.ok is False
    assert "expected JSON" in probe_result.detail
    assert completion_result.status_code == 502
    assert completion_result.body["error"]["type"] == "invalid_provider_response"
    assert "expected JSON" in completion_result.body["error"]["message"]


def test_openai_compatible_adapter_reads_top_level_error_message(monkeypatch):
    provider = Provider(
        id=1,
        name="Mock",
        code="mock",
        provider_type="openai",
        base_url="http://127.0.0.1:8010/v1",
        api_key_encrypted="plain:key",
        default_model="mock-model",
        enabled=True,
        timeout_ms=30000,
        max_retries=1,
        extra_config_json={},
    )
    adapter = OpenAICompatibleProviderAdapter(provider)

    monkeypatch.setattr(
        "api.providers.openai_compatible.httpx.post",
        lambda *args, **kwargs: DummyResponse(
            403,
            {"code": "SUBSCRIPTION_NOT_FOUND", "message": "No active subscription found for this group"},
        ),
    )

    probe_result = adapter.probe()

    assert probe_result.ok is False
    assert probe_result.detail == "http 403: No active subscription found for this group"
