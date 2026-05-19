from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from admin.schemas import ExecutionTaskCreateRequest
from admin.schemas import ExecutionTaskListResponse
from admin.schemas import ExecutionTaskResponse
from data.db import get_db_session
from task.services.execution_service import ExecutionService


router = APIRouter(prefix="/admin/execution-tasks", tags=["execution-tasks"])


def _to_response(task) -> ExecutionTaskResponse:
    return ExecutionTaskResponse(
        id=task.id,
        name=task.name,
        source_type=task.source_type,
        source_ref_id=task.source_ref_id,
        status=task.status,
        progress_total=task.progress_total,
        progress_done=task.progress_done,
    )


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


@router.post("/{task_id}/start", response_model=ExecutionTaskResponse)
def start_execution_task(task_id: int, session: Session = Depends(get_db_session)) -> ExecutionTaskResponse:
    service = ExecutionService(session)
    task = service.start_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _to_response(task)


@router.post("/{task_id}/stop", response_model=ExecutionTaskResponse)
def stop_execution_task(task_id: int, session: Session = Depends(get_db_session)) -> ExecutionTaskResponse:
    service = ExecutionService(session)
    task = service.stop_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _to_response(task)


@router.post("/{task_id}/retry", response_model=ExecutionTaskResponse)
def retry_execution_task(task_id: int, session: Session = Depends(get_db_session)) -> ExecutionTaskResponse:
    service = ExecutionService(session)
    task = service.retry_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _to_response(task)


@router.get("/{task_id}/results")
def list_execution_task_results(task_id: int, session: Session = Depends(get_db_session)):
    service = ExecutionService(session)
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    results = service.repository.list_results(task_id)
    return {
        "items": [
            {
                "id": result.id,
                "provider_id": result.provider_id,
                "model": result.model,
                "success": result.success,
                "http_status": result.http_status,
            }
            for result in results
        ]
    }
