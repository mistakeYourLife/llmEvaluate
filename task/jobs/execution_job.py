from sqlalchemy.orm import Session

from api.providers.base import build_provider_adapter
from data.models import RecordedRequest
from data.repositories.provider_repository import ProviderRepository
from data.repositories.execution_repository import ExecutionRepository


def run_execution_task(session: Session, task_id: int) -> int:
    repository = ExecutionRepository(session)
    provider_repository = ProviderRepository(session)
    task = repository.get_task(task_id)
    if task is None:
        raise ValueError(f"execution task {task_id} not found")

    repository.update_status(task_id, "running")

    source_request = None
    if task.source_type == "recorded_request":
        source_request = session.get(RecordedRequest, task.source_ref_id)

    provider_ids = task.target_provider_ids_json.get("ids", [])
    models = task.target_models_json.get("models", [])
    total = len(provider_ids)
    repository.update_progress(task_id, total=total, done=0)

    for index, provider_id in enumerate(provider_ids, start=1):
        provider = provider_repository.get_by_id(provider_id)
        model = models[0] if models else None
        if provider is not None and model is None:
            model = provider.default_model
        request_body = dict(source_request.request_body_json) if source_request else {}
        if model is not None:
            request_body["model"] = model
        if provider is None:
            repository.create_result(
                execution_task_id=task.id,
                source_request_id=source_request.id if source_request else None,
                sample_id=None,
                provider_id=provider_id,
                model=model,
                run_index=0,
                request_body_json=request_body,
                response_body_json={"error": {"message": "provider not found"}},
                output_text=None,
                http_status=404,
                success=False,
                error_code="provider_not_found",
                error_message="provider not found",
            )
            repository.update_progress(task_id, total=total, done=index)
            continue

        adapter = build_provider_adapter(provider)
        provider_response = adapter.chat_completions(request_body, model=model)
        repository.create_result(
            execution_task_id=task.id,
            source_request_id=source_request.id if source_request else None,
            sample_id=None,
            provider_id=provider_id,
            model=model,
            run_index=0,
            request_body_json=request_body,
            response_body_json=provider_response.body,
            output_text=provider_response.output_text,
            http_status=provider_response.status_code,
            success=provider_response.status_code < 400,
            first_token_latency_ms=provider_response.first_token_latency_ms,
            complete_latency_ms=provider_response.complete_latency_ms,
            prompt_tokens=provider_response.prompt_tokens,
            completion_tokens=provider_response.completion_tokens,
            total_tokens=provider_response.total_tokens,
            tokens_per_second=int(provider_response.tokens_per_second)
            if provider_response.tokens_per_second is not None
            else None,
            error_code=None if provider_response.status_code < 400 else "provider_error",
            error_message=None
            if provider_response.status_code < 400
            else str(provider_response.body.get("error", provider_response.body)),
        )
        repository.update_progress(task_id, total=total, done=index)

    repository.update_status(task_id, "completed")
    return total
