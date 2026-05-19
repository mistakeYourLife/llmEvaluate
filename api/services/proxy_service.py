from dataclasses import dataclass

from sqlalchemy.orm import Session

from api.providers.base import ProviderChatCompletionResult
from api.providers.base import build_provider_adapter
from data.repositories.provider_repository import ProviderRepository
from data.repositories.recording_repository import RecordingRepository
from data.schemas.recording import RecordedRequestCreate
from data.schemas.recording import RecordedResponseCreate


@dataclass(slots=True)
class ProxyServiceResult:
    status_code: int
    body: dict


class ProxyService:
    def __init__(self, session: Session):
        self.session = session
        self.recording_repository = RecordingRepository(session)
        self.provider_repository = ProviderRepository(session)

    def handle_chat_completions(self, payload: dict) -> ProxyServiceResult:
        provider = self.provider_repository.get_first_enabled()

        if provider is None:
            return ProxyServiceResult(
                status_code=400,
                body={"error": {"message": "no enabled provider configured", "type": "no_provider"}},
            )

        resolved_model = payload.get("model") or provider.default_model
        forward_payload = dict(payload)
        forward_payload["model"] = resolved_model
        adapter = build_provider_adapter(provider)

        recorded_request = self.recording_repository.create_request(
            RecordedRequestCreate(
                provider_id=provider.id,
                request_type="chat_completions",
                model=resolved_model,
                is_stream=bool(payload.get("stream", False)),
                request_body_json=forward_payload,
                request_headers_json={},
                request_text_snapshot=str(forward_payload),
            )
        )
        provider_response = adapter.chat_completions(forward_payload, model=resolved_model)
        self.recording_repository.create_response(
            RecordedResponseCreate(
                request_id=recorded_request.id,
                http_status=provider_response.status_code,
                response_body_json=provider_response.body,
                response_headers_json=provider_response.headers,
                response_text_snapshot=str(provider_response.body),
                first_token_latency_ms=provider_response.first_token_latency_ms,
                complete_latency_ms=provider_response.complete_latency_ms,
                prompt_tokens=provider_response.prompt_tokens,
                completion_tokens=provider_response.completion_tokens,
                total_tokens=provider_response.total_tokens,
                tokens_per_second=int(provider_response.tokens_per_second)
                if provider_response.tokens_per_second is not None
                else None,
                error_code=None if provider_response.status_code < 400 else "provider_error",
                error_message=None
                if provider_response.status_code < 400
                else str(provider_response.body.get("error", provider_response.body)),
            )
        )
        return ProxyServiceResult(status_code=provider_response.status_code, body=provider_response.body)
