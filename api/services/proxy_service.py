from sqlalchemy.orm import Session

from data.repositories.provider_repository import ProviderRepository
from data.repositories.recording_repository import RecordingRepository
from data.schemas.recording import RecordedRequestCreate
from data.schemas.recording import RecordedResponseCreate


class ProxyService:
    def __init__(self, session: Session):
        self.session = session
        self.recording_repository = RecordingRepository(session)
        self.provider_repository = ProviderRepository(session)

    def handle_chat_completions(self, payload: dict) -> dict:
        provider = next((item for item in self.provider_repository.list_all() if item.enabled), None)

        recorded_request = self.recording_repository.create_request(
            RecordedRequestCreate(
                provider_id=provider.id if provider else 0,
                request_type="chat_completions",
                model=payload.get("model"),
                is_stream=bool(payload.get("stream", False)),
                request_body_json=payload,
                request_headers_json={},
                request_text_snapshot=str(payload),
            )
        )

        if provider is None:
            response_payload = {"error": "no enabled provider configured"}
            self.recording_repository.create_response(
                RecordedResponseCreate(
                    request_id=recorded_request.id,
                    http_status=400,
                    response_body_json=response_payload,
                    response_headers_json={},
                    response_text_snapshot=str(response_payload),
                    error_code="no_provider",
                    error_message="no enabled provider configured",
                )
            )
            return response_payload

        response_payload = {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "choices": [],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "request_echo": payload,
        }
        self.recording_repository.create_response(
            RecordedResponseCreate(
                request_id=recorded_request.id,
                http_status=200,
                response_body_json=response_payload,
                response_headers_json={},
                response_text_snapshot=str(response_payload),
                first_token_latency_ms=0,
                complete_latency_ms=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                tokens_per_second=0,
            )
        )
        return response_payload
