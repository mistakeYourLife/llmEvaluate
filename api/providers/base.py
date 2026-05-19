from dataclasses import dataclass
from typing import Protocol

from data.models import Provider


@dataclass(slots=True)
class ProviderProbeResult:
    ok: bool
    detail: str


class ProviderAdapter(Protocol):
    def probe(self) -> ProviderProbeResult:
        ...


def build_provider_adapter(provider: Provider) -> ProviderAdapter:
    from api.providers.openai_compatible import OpenAICompatibleProviderAdapter

    return OpenAICompatibleProviderAdapter(provider)
