from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from fastapi import status
from sqlalchemy.orm import Session

from admin.schemas import EvaluationTaskCreateRequest
from admin.schemas import EvaluationTaskListResponse
from admin.schemas import EvaluationTaskResponse
from data.db import get_db_session
from data.repositories.evaluation_repository import EvaluationRepository
from task.jobs.evaluation_job import run_evaluation_task


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


def _get_database_url(session: Session) -> str:
    return str(session.get_bind().url)


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
def start_evaluation_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db_session),
) -> EvaluationTaskResponse:
    repository = EvaluationRepository(session)
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status == "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该评估任务正在运行中，请勿重复启动。")
    repository.delete_scores(task_id)
    repository.update_progress(task_id, total=0, done=0)
    started = repository.update_status(task_id, "running")
    session.commit()
    background_tasks.add_task(run_evaluation_task, task_id, _get_database_url(session))
    return _to_response(started)


@router.post("/{task_id}/retry", response_model=EvaluationTaskResponse)
def retry_evaluation_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db_session),
) -> EvaluationTaskResponse:
    repository = EvaluationRepository(session)
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status == "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该评估任务正在运行中，请稍后再重跑。")
    repository.delete_scores(task_id)
    repository.update_progress(task_id, total=0, done=0)
    started = repository.update_status(task_id, "running")
    session.commit()
    background_tasks.add_task(run_evaluation_task, task_id, _get_database_url(session))
    return _to_response(started)


@router.get("/{task_id}/scores")
def list_evaluation_scores(task_id: int, session: Session = Depends(get_db_session)):
    repository = EvaluationRepository(session)
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    scores = repository.list_scores(task_id)
    return {
        "items": [
            {
                "id": score.id,
                "execution_result_id": score.execution_result_id,
                "score": score.score,
                "verdict": score.verdict,
                "reasoning_summary": score.reasoning_summary,
                "dimension_scores_json": score.dimension_scores_json,
                "judge_model": score.judge_model,
            }
            for score in scores
        ]
    }


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evaluation_task(task_id: int, session: Session = Depends(get_db_session)) -> Response:
    repository = EvaluationRepository(session)
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not repository.can_delete_task(task_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该评估任务已运行或已生成评分结果，暂不允许删除。")
    repository.delete_task(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
