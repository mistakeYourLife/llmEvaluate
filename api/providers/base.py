from dataclasses import dataclass
from typing import Protocol

from data.models import Provider


@dataclass(slots=True)
class ProviderProbeResult:
    ok: bool
    detail: str


@dataclass(slots=True)
class ProviderChatCompletionResult:
    status_code: int
    body: dict
    headers: dict
    first_token_latency_ms: int | None
    complete_latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    tokens_per_second: float | None
    output_text: str | None


class ProviderAdapter(Protocol):
    def probe(self) -> ProviderProbeResult:
        ...

    def chat_completions(
        self,
        payload: dict,
        model: str | None = None,
    ) -> ProviderChatCompletionResult:
        ...


def build_provider_adapter(provider: Provider) -> ProviderAdapter:
    from api.providers.openai_compatible import OpenAICompatibleProviderAdapter

    return OpenAICompatibleProviderAdapter(provider)
