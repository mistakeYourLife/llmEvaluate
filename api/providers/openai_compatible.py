import time

import httpx

from api.providers.base import ProviderChatCompletionResult
from api.providers.base import ProviderProbeResult
from data.models import Provider


class OpenAICompatibleProviderAdapter:
    def __init__(self, provider: Provider):
        self.provider = provider

    def probe(self) -> ProviderProbeResult:
        request_payload = {
            "model": self.provider.default_model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "temperature": 0,
            "stream": False,
        }
        url = self.provider.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._plain_api_key()}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(
                url,
                headers=headers,
                json=request_payload,
                timeout=self.provider.timeout_ms / 1000,
                trust_env=False,
            )
            validation_error = self._validate_success_response(response)
            if response.status_code < 400 and validation_error is None:
                return ProviderProbeResult(ok=True, detail=f"model_available:{self.provider.default_model}")
            if response.status_code < 400:
                return ProviderProbeResult(ok=False, detail=validation_error or "invalid response")

            error_detail = f"http {response.status_code}"
            try:
                body = response.json()
                if isinstance(body, dict):
                    error = body.get("error")
                    if isinstance(error, dict):
                        message = error.get("message")
                        if isinstance(message, str) and message:
                            error_detail = f"{error_detail}: {message}"
                    elif isinstance(body.get("message"), str) and body.get("message"):
                        error_detail = f"{error_detail}: {body['message']}"
            except ValueError:
                if response.text:
                    error_detail = f"{error_detail}: {response.text[:200]}"
            return ProviderProbeResult(ok=False, detail=error_detail)
        except httpx.HTTPError as exc:
            return ProviderProbeResult(ok=False, detail=str(exc))

    def chat_completions(
        self,
        payload: dict,
        model: str | None = None,
    ) -> ProviderChatCompletionResult:
        request_payload = dict(payload)
        resolved_model = model or request_payload.get("model") or self.provider.default_model
        request_payload["model"] = resolved_model
        url = self.provider.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._plain_api_key()}",
            "Content-Type": "application/json",
        }
        started_at = time.perf_counter()
        try:
            response = httpx.post(
                url,
                headers=headers,
                json=request_payload,
                timeout=self.provider.timeout_ms / 1000,
                trust_env=False,
            )
            complete_latency_ms = int((time.perf_counter() - started_at) * 1000)
            validation_error = self._validate_success_response(response) if response.status_code < 400 else None
            if validation_error is not None:
                error_body = {"error": {"message": validation_error, "type": "invalid_provider_response"}}
                return ProviderChatCompletionResult(
                    status_code=502,
                    body=error_body,
                    headers=dict(response.headers),
                    first_token_latency_ms=complete_latency_ms,
                    complete_latency_ms=complete_latency_ms,
                    prompt_tokens=None,
                    completion_tokens=None,
                    total_tokens=None,
                    tokens_per_second=None,
                    output_text=None,
                )

            try:
                body = response.json()
            except ValueError:
                body = {"raw_text": response.text}

            usage = body.get("usage", {}) if isinstance(body, dict) else {}
            completion_tokens = usage.get("completion_tokens")
            tokens_per_second = None
            if completion_tokens is not None and complete_latency_ms > 0:
                tokens_per_second = completion_tokens / (complete_latency_ms / 1000)

            return ProviderChatCompletionResult(
                status_code=response.status_code,
                body=body if isinstance(body, dict) else {"body": body},
                headers=dict(response.headers),
                first_token_latency_ms=complete_latency_ms,
                complete_latency_ms=complete_latency_ms,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=completion_tokens,
                total_tokens=usage.get("total_tokens"),
                tokens_per_second=tokens_per_second,
                output_text=self._extract_output_text(body if isinstance(body, dict) else {}),
            )
        except httpx.HTTPError as exc:
            error_body = {"error": {"message": str(exc), "type": "provider_request_error"}}
            return ProviderChatCompletionResult(
                status_code=502,
                body=error_body,
                headers={},
                first_token_latency_ms=None,
                complete_latency_ms=int((time.perf_counter() - started_at) * 1000),
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                tokens_per_second=None,
                output_text=None,
            )

    def _plain_api_key(self) -> str:
        return self.provider.api_key_encrypted.removeprefix("plain:")

    def _validate_success_response(self, response: httpx.Response) -> str | None:
        try:
            body = response.json()
        except ValueError:
            return self._format_invalid_response(
                "expected JSON",
                response.headers.get("content-type"),
                response.text,
            )

        if not isinstance(body, dict):
            return "provider returned an invalid OpenAI response: expected JSON object"
        if isinstance(body.get("error"), dict):
            error_message = body["error"].get("message")
            if isinstance(error_message, str) and error_message:
                return f"provider returned an error payload: {error_message}"
            return "provider returned an error payload"
        if not self._looks_like_chat_completion(body):
            return "provider returned an invalid OpenAI response: missing choices"
        return None

    @staticmethod
    def _looks_like_chat_completion(body: dict) -> bool:
        choices = body.get("choices")
        return isinstance(choices, list) and len(choices) > 0

    @staticmethod
    def _format_invalid_response(reason: str, content_type: str | None, raw_text: str) -> str:
        prefix = "provider returned an invalid OpenAI response"
        parts = [reason]
        if content_type:
            parts.append(f"content-type={content_type}")
        snippet = raw_text.strip().replace("\n", " ")
        if snippet:
            parts.append(f"snippet={snippet[:120]}")
        return f"{prefix}: {'; '.join(parts)}"

    @staticmethod
    def _extract_output_text(body: dict) -> str | None:
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return None
        message = first_choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
        text = first_choice.get("text")
        if isinstance(text, str):
            return text
        return None
