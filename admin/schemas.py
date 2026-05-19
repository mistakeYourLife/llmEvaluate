from pydantic import BaseModel
from pydantic import ConfigDict


class ProviderCreateRequest(BaseModel):
    name: str
    code: str
    provider_type: str
    base_url: str
    api_key: str
    default_model: str


class ProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    provider_type: str
    base_url: str
    default_model: str
    enabled: bool


class ProviderUpdateRequest(BaseModel):
    name: str | None = None
    base_url: str | None = None
    default_model: str | None = None


class ProviderProbeResponse(BaseModel):
    ok: bool
    detail: str
