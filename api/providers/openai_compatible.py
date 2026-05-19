import httpx

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

    def _plain_api_key(self) -> str:
        return self.provider.api_key_encrypted.removeprefix("plain:")
