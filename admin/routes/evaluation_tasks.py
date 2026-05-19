from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from admin.schemas import EvaluationTaskCreateRequest
from admin.schemas import EvaluationTaskListResponse
from admin.schemas import EvaluationTaskResponse
from data.db import get_db_session
from data.repositories.evaluation_repository import EvaluationRepository


router = APIRouter(prefix="/admin/evaluation-tasks", tags=["evaluation-tasks"])


def _to_response(task) -> EvaluationTaskResponse:
    return EvaluationTaskResponse(
        id=task.id,
        name=task.name,
        source_type=task.source_type,
        source_ref_id=task.source_ref_id,
        evaluator_type=task.evaluator_type,
        judge_provider_id=task.judge_provider_id,
        judge_model=task.judge_model,
        status=task.status,
        progress_total=task.progress_total,
        progress_done=task.progress_done,
    )


@router.post("", response_model=EvaluationTaskResponse, status_code=status.HTTP_201_CREATED)
def create_evaluation_task(
    payload: EvaluationTaskCreateRequest,
    session: Session = Depends(get_db_session),
) -> EvaluationTaskResponse:
    repository = EvaluationRepository(session)
    task = repository.create_task(
        name=payload.name,
        source_type=payload.source_type,
        source_ref_id=payload.source_ref_id,
        evaluator_type=payload.evaluator_type,
        judge_provider_id=payload.judge_provider_id,
        judge_model=payload.judge_model,
        task_config_json=payload.task_config_json,
    )
    return _to_response(task)


@router.get("", response_model=EvaluationTaskListResponse)
def list_evaluation_tasks(session: Session = Depends(get_db_session)) -> EvaluationTaskListResponse:
    repository = EvaluationRepository(session)
    return EvaluationTaskListResponse(items=[_to_response(task) for task in repository.list_tasks()])


@router.get("/{task_id}", response_model=EvaluationTaskResponse)
def get_evaluation_task(task_id: int, session: Session = Depends(get_db_session)) -> EvaluationTaskResponse:
    repository = EvaluationRepository(session)
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _to_response(task)


@router.post("/{task_id}/start", response_model=EvaluationTaskResponse)
def start_evaluation_task(task_id: int, session: Session = Depends(get_db_session)) -> EvaluationTaskResponse:
    repository = EvaluationRepository(session)
    task = repository.update_status(task_id, "running")
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _to_response(task)


@router.post("/{task_id}/retry", response_model=EvaluationTaskResponse)
def retry_evaluation_task(task_id: int, session: Session = Depends(get_db_session)) -> EvaluationTaskResponse:
    repository = EvaluationRepository(session)
    task = repository.update_status(task_id, "pending")
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _to_response(task)


@router.get("/{task_id}/scores")
def list_evaluation_scores(task_id: int, session: Session = Depends(get_db_session)):
    repository = EvaluationRepository(session)
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return {"items": []}
