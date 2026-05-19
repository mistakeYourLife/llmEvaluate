from sqlalchemy.orm import Session

from data.models import RecordedRequest
from data.repositories.execution_repository import ExecutionRepository


def run_execution_task(session: Session, task_id: int) -> int:
    repository = ExecutionRepository(session)
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
        model = models[0] if models else None
        request_body = source_request.request_body_json if source_request else {}
        response_body = {"mock": True, "provider_id": provider_id, "model": model}
        repository.create_result(
            execution_task_id=task.id,
            source_request_id=source_request.id if source_request else None,
            sample_id=None,
            provider_id=provider_id,
            model=model,
            run_index=0,
            request_body_json=request_body,
            response_body_json=response_body,
            output_text=str(response_body),
            http_status=200,
            success=True,
            first_token_latency_ms=0,
            complete_latency_ms=0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            tokens_per_second=0,
        )
        repository.update_progress(task_id, total=total, done=index)

    repository.update_status(task_id, "completed")
    return total
