from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from admin.schemas import ExecutionTaskCreateRequest
from admin.schemas import ExecutionResultDetailResponse
from admin.schemas import ExecutionResultItemResponse
from admin.schemas import ExecutionResultListResponse
from admin.schemas import ExecutionTaskListResponse
from admin.schemas import ExecutionTaskResponse
from admin.schemas import ExecutionTaskUpdateRequest
from data.db import get_db_session
from task.jobs.execution_job import run_execution_task
from task.services.execution_service import ExecutionService
from task.services.execution_service import normalize_run_count


router = APIRouter(prefix="/admin/execution-tasks", tags=["execution-tasks"])


def _to_response(task) -> ExecutionTaskResponse:
    return ExecutionTaskResponse(
        id=task.id,
        name=task.name,
        source_type=task.source_type,
        source_ref_id=task.source_ref_id,
        target_provider_ids_json=task.target_provider_ids_json,
        target_models_json=task.target_models_json,
        status=task.status,
        progress_total=task.progress_total,
        progress_done=task.progress_done,
        run_count=normalize_run_count(task.task_config_json),
    )


def _to_result_item(result) -> ExecutionResultItemResponse:
    return ExecutionResultItemResponse(
        id=result.id,
        provider_id=result.provider_id,
        model=result.model,
        run_index=result.run_index,
        success=result.success,
        http_status=result.http_status,
        first_token_latency_ms=result.first_token_latency_ms,
        complete_latency_ms=result.complete_latency_ms,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
        tokens_per_second=result.tokens_per_second,
        error_code=result.error_code,
        error_message=result.error_message,
    )


def _to_result_detail(result) -> ExecutionResultDetailResponse:
    return ExecutionResultDetailResponse(
        id=result.id,
        execution_task_id=result.execution_task_id,
        source_request_id=result.source_request_id,
        sample_id=result.sample_id,
        provider_id=result.provider_id,
        model=result.model,
        run_index=result.run_index,
        request_body_json=result.request_body_json,
        response_body_json=result.response_body_json,
        output_text=result.output_text,
        http_status=result.http_status,
        first_token_latency_ms=result.first_token_latency_ms,
        complete_latency_ms=result.complete_latency_ms,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
        tokens_per_second=result.tokens_per_second,
        success=result.success,
        error_code=result.error_code,
        error_message=result.error_message,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


def _get_database_url(session: Session) -> str:
    return str(session.get_bind().url)


@router.post("", response_model=ExecutionTaskResponse, status_code=status.HTTP_201_CREATED)
def create_execution_task(
    payload: ExecutionTaskCreateRequest,
    session: Session = Depends(get_db_session),
) -> ExecutionTaskResponse:
    service = ExecutionService(session)
    task = service.create_task(
        name=payload.name,
        source_type=payload.source_type,
        source_ref_id=payload.source_ref_id,
        target_provider_ids_json=payload.target_provider_ids_json,
        target_models_json=payload.target_models_json,
        task_config_json=payload.task_config_json,
    )
    return _to_response(task)


@router.get("", response_model=ExecutionTaskListResponse)
def list_execution_tasks(session: Session = Depends(get_db_session)) -> ExecutionTaskListResponse:
    service = ExecutionService(session)
    return ExecutionTaskListResponse(items=[_to_response(task) for task in service.list_tasks()])


@router.get("/{task_id}", response_model=ExecutionTaskResponse)
def get_execution_task(task_id: int, session: Session = Depends(get_db_session)) -> ExecutionTaskResponse:
    service = ExecutionService(session)
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _to_response(task)


@router.put("/{task_id}", response_model=ExecutionTaskResponse)
def update_execution_task(
    task_id: int,
    payload: ExecutionTaskUpdateRequest,
    session: Session = Depends(get_db_session),
) -> ExecutionTaskResponse:
    service = ExecutionService(session)
    task = service.update_task_name(task_id, payload.name)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _to_response(task)


@router.post("/{task_id}/start", response_model=ExecutionTaskResponse)
def start_execution_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db_session),
) -> ExecutionTaskResponse:
    service = ExecutionService(session)
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status == "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该执行任务正在运行中，请勿重复启动。")
    service.repository.delete_results(task_id)
    service.repository.update_progress(task_id, total=0, done=0)
    started = service.start_task(task_id)
    session.commit()
    background_tasks.add_task(run_execution_task, task_id, _get_database_url(session))
    return _to_response(started)


@router.post("/{task_id}/stop", response_model=ExecutionTaskResponse)
def stop_execution_task(task_id: int, session: Session = Depends(get_db_session)) -> ExecutionTaskResponse:
    service = ExecutionService(session)
    task = service.stop_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _to_response(task)


@router.post("/{task_id}/retry", response_model=ExecutionTaskResponse)
def retry_execution_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db_session),
) -> ExecutionTaskResponse:
    service = ExecutionService(session)
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status == "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该执行任务正在运行中，请先停止后再重跑。")
    service.repository.delete_results(task_id)
    service.repository.update_progress(task_id, total=0, done=0)
    started = service.start_task(task_id)
    session.commit()
    background_tasks.add_task(run_execution_task, task_id, _get_database_url(session))
    return _to_response(started)


@router.get("/{task_id}/results", response_model=ExecutionResultListResponse)
def list_execution_task_results(task_id: int, session: Session = Depends(get_db_session)) -> ExecutionResultListResponse:
    service = ExecutionService(session)
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    results = service.repository.list_results(task_id)
    return ExecutionResultListResponse(items=[_to_result_item(result) for result in results])


@router.get("/{task_id}/results/{result_id}", response_model=ExecutionResultDetailResponse)
def get_execution_task_result(
    task_id: int,
    result_id: int,
    session: Session = Depends(get_db_session),
) -> ExecutionResultDetailResponse:
    service = ExecutionService(session)
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    result = service.repository.get_result(result_id)
    if result is None or result.execution_task_id != task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution result not found")

    return _to_result_detail(result)
