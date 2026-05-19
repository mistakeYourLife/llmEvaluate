from pydantic import BaseModel
from pydantic import Field


class RecordedRequestCreate(BaseModel):
    provider_id: int
    request_type: str
    source_app: str | None = None
    model: str | None = None
    is_stream: bool = False
    request_headers_json: dict = Field(default_factory=dict)
    request_body_json: dict = Field(default_factory=dict)
    request_text_snapshot: str | None = None


class RecordedResponseCreate(BaseModel):
    request_id: int
    http_status: int | None = None
    response_headers_json: dict = Field(default_factory=dict)
    response_body_json: dict = Field(default_factory=dict)
    response_text_snapshot: str | None = None
    first_token_latency_ms: int | None = None
    complete_latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    tokens_per_second: int | None = None
    error_code: str | None = None
    error_message: str | None = None
