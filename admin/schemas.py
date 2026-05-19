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


class RecordItemResponse(BaseModel):
    id: int
    provider_id: int
    request_type: str
    model: str | None = None
    is_stream: bool
    http_status: int | None = None
    response_id: int | None = None


class RecordListResponse(BaseModel):
    items: list[RecordItemResponse]


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
    status: str
    progress_total: int
    progress_done: int


class ExecutionTaskListResponse(BaseModel):
    items: list[ExecutionTaskResponse]


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
