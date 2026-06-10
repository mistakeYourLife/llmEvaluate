import logging

from api.providers.base import build_provider_adapter
from data.db import get_session_factory
from data.models import RecordedRequest
from data.repositories.provider_repository import ProviderRepository
from data.repositories.execution_repository import ExecutionRepository
from task.services.execution_service import normalize_run_count


logger = logging.getLogger(__name__)


def _commit(session) -> None:
    session.commit()
    session.expire_all()


def _mark_task_failed(session, task_id: int) -> None:
    repository = ExecutionRepository(session)
    task = repository.get_task(task_id)
    if task is None:
        return
    repository.update_status(task_id, "failed")
    _commit(session)


def run_execution_task(task_id: int, database_url: str | None = None) -> int:
    session_factory = get_session_factory(database_url)
    with session_factory() as session:
        try:
            return _run_execution_task(session, task_id)
        except Exception:
            session.rollback()
            _mark_task_failed(session, task_id)
            logger.exception("Execution task %s failed", task_id)
            return 0


def _run_execution_task(session, task_id: int) -> int:
    repository = ExecutionRepository(session)
    provider_repository = ProviderRepository(session)
    task = repository.get_task(task_id)
    if task is None:
        raise ValueError(f"execution task {task_id} not found")

    repository.update_status(task_id, "running")
    _commit(session)

    source_request = None
    if task.source_type == "recorded_request":
        source_request = session.get(RecordedRequest, task.source_ref_id)

    provider_ids = task.target_provider_ids_json.get("ids", [])
    models = task.target_models_json.get("models", [])
    run_count = normalize_run_count(task.task_config_json)
    total = len(provider_ids) * run_count
    repository.update_progress(task_id, total=total, done=0)
    _commit(session)

    processed = 0

    for provider_id in provider_ids:
        provider = provider_repository.get_by_id(provider_id)
        base_model = models[0] if models else None
        if provider is not None and base_model is None:
            base_model = provider.default_model

        for run_index in range(run_count):
            current_task = repository.get_task(task_id)
            if current_task is None:
                raise ValueError(f"execution task {task_id} not found")
            if current_task.status == "stopped":
                return processed

            request_body = dict(source_request.request_body_json) if source_request else {}
            if base_model is not None:
                request_body["model"] = base_model
            if provider is None:
                repository.create_result(
                    execution_task_id=task.id,
                    source_request_id=source_request.id if source_request else None,
                    sample_id=None,
                    provider_id=provider_id,
                    model=base_model,
                    run_index=run_index,
                    request_body_json=request_body,
                    response_body_json={"error": {"message": "provider not found"}},
                    output_text=None,
                    http_status=404,
                    success=False,
                    error_code="provider_not_found",
                    error_message="provider not found",
                )
                processed += 1
                repository.update_progress(task_id, total=total, done=processed)
                _commit(session)
                continue

            try:
                adapter = build_provider_adapter(provider)
                provider_response = adapter.chat_completions(request_body, model=base_model)
            except Exception as exc:
                repository.create_result(
                    execution_task_id=task.id,
                    source_request_id=source_request.id if source_request else None,
                    sample_id=None,
                    provider_id=provider_id,
                    model=base_model,
                    run_index=run_index,
                    request_body_json=request_body,
                    response_body_json={"error": {"message": str(exc)}},
                    output_text=None,
                    http_status=None,
                    success=False,
                    error_code="provider_request_failed",
                    error_message=str(exc),
                )
                processed += 1
                repository.update_progress(task_id, total=total, done=processed)
                _commit(session)
                continue

            repository.create_result(
                execution_task_id=task.id,
                source_request_id=source_request.id if source_request else None,
                sample_id=None,
                provider_id=provider_id,
                model=base_model,
                run_index=run_index,
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
            processed += 1
            repository.update_progress(task_id, total=total, done=processed)
            _commit(session)

    current_task = repository.get_task(task_id)
    if current_task is not None and current_task.status != "stopped":
        repository.update_status(task_id, "completed")
        _commit(session)

    return processed
