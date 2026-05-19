import time

import httpx

from api.providers.base import ProviderChatCompletionResult
from api.providers.base import ProviderProbeResult
from data.models import Provider


class OpenAICompatibleProviderAdapter:
    def __init__(self, provider: Provider):
        self.provider = provider

    def probe(self) -> ProviderProbeResult:
        url = self.provider.base_url.rstrip("/") + "/models"
        headers = {"Authorization": f"Bearer {self._plain_api_key()}"}
        try:
            response = httpx.get(url, headers=headers, timeout=self.provider.timeout_ms / 1000)
            if response.status_code < 400:
                return ProviderProbeResult(ok=True, detail="reachable")
            return ProviderProbeResult(ok=False, detail=f"http {response.status_code}")
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
            )
            complete_latency_ms = int((time.perf_counter() - started_at) * 1000)
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
