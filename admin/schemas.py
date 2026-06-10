from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ProviderCreateRequest(BaseModel):
    name: str
    code: str
    provider_type: str
    base_url: str
    api_key: str
    default_model: str
    timeout_ms: int = Field(default=30000, gt=0)


class ProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    provider_type: str
    base_url: str
    default_model: str
    timeout_ms: int
    enabled: bool
    is_default: bool


class ProviderListResponse(BaseModel):
    items: list[ProviderResponse]


class ProviderUpdateRequest(BaseModel):
    name: str | None = None
    base_url: str | None = None
    default_model: str | None = None
    api_key: str | None = None
    timeout_ms: int | None = Field(default=None, gt=0)


class ProviderProbeResponse(BaseModel):
    ok: bool
    detail: str


class RecordItemResponse(BaseModel):
    id: int
    name: str
    provider_id: int
    request_type: str
    model: str | None = None
    is_stream: bool
    http_status: int | None = None
    response_id: int | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class RecordResponseDetailResponse(BaseModel):
    id: int | None = None
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
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RecordDetailResponse(RecordItemResponse):
    source_app: str | None = None
    request_headers_json: dict = Field(default_factory=dict)
    request_body_json: dict = Field(default_factory=dict)
    request_text_snapshot: str | None = None
    response: RecordResponseDetailResponse


class RecordListResponse(BaseModel):
    items: list[RecordItemResponse]


class RecordUpdateRequest(BaseModel):
    name: str = Field(default="", max_length=255)


class ExecutionTaskCreateRequest(BaseModel):
    name: str
    source_type: str
    source_ref_id: int
    target_provider_ids_json: dict
    target_models_json: dict
    task_config_json: dict = {}


class ExecutionTaskResponse(BaseModel):
    id: int
    name: str
    source_type: str
    source_ref_id: int
    target_provider_ids_json: dict = Field(default_factory=dict)
    target_models_json: dict = Field(default_factory=dict)
    status: str
    progress_total: int
    progress_done: int
    run_count: int = 1


class ExecutionTaskListResponse(BaseModel):
    items: list[ExecutionTaskResponse]


class ExecutionTaskUpdateRequest(BaseModel):
    name: str = Field(default="", max_length=255)


class ExecutionResultItemResponse(BaseModel):
    id: int
    provider_id: int
    model: str | None = None
    run_index: int
    success: bool
    http_status: int | None = None
    first_token_latency_ms: int | None = None
    complete_latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    tokens_per_second: int | None = None
    error_code: str | None = None
    error_message: str | None = None


class ExecutionResultDetailResponse(ExecutionResultItemResponse):
    execution_task_id: int
    source_request_id: int | None = None
    sample_id: int | None = None
    run_index: int
    request_body_json: dict = Field(default_factory=dict)
    response_body_json: dict = Field(default_factory=dict)
    output_text: str | None = None
    created_at: datetime
    updated_at: datetime


class ExecutionResultListResponse(BaseModel):
    items: list[ExecutionResultItemResponse]


class EvaluationTaskCreateRequest(BaseModel):
    name: str
    source_type: str
    source_ref_id: int
    evaluator_type: str
    judge_provider_id: int
    judge_model: str
    task_config_json: dict = {}


class EvaluationTaskResponse(BaseModel):
    id: int
    name: str
    source_type: str
    source_ref_id: int
    evaluator_type: str
    judge_provider_id: int
    judge_model: str
    status: str
    progress_total: int
    progress_done: int


class EvaluationTaskListResponse(BaseModel):
    items: list[EvaluationTaskResponse]
