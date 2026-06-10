from sqlalchemy.orm import Session

from data.models import EvaluationScore
from data.models import EvaluationTask


class EvaluationRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_task(
        self,
        *,
        name: str,
        source_type: str,
        source_ref_id: int,
        evaluator_type: str,
        judge_provider_id: int,
        judge_model: str,
        task_config_json: dict,
    ) -> EvaluationTask:
        task = EvaluationTask(
            name=name,
            source_type=source_type,
            source_ref_id=source_ref_id,
            evaluator_type=evaluator_type,
            judge_provider_id=judge_provider_id,
            judge_model=judge_model,
            status="pending",
            progress_total=0,
            progress_done=0,
            task_config_json=task_config_json,
        )
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def list_tasks(self) -> list[EvaluationTask]:
        return self.session.query(EvaluationTask).order_by(EvaluationTask.id.desc()).all()

    def get_task(self, task_id: int) -> EvaluationTask | None:
        return self.session.get(EvaluationTask, task_id)

    def update_status(self, task_id: int, status: str) -> EvaluationTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        task.status = status
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def update_progress(self, task_id: int, *, total: int, done: int) -> EvaluationTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        task.progress_total = total
        task.progress_done = done
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def create_score(
        self,
        *,
        evaluation_task_id: int,
        execution_result_id: int,
        evaluator_type: str,
        judge_provider_id: int,
        judge_model: str,
        score: float,
        dimension_scores_json: dict,
        verdict: str | None,
        reasoning_summary: str | None,
        raw_judge_response_json: dict,
    ) -> EvaluationScore:
        item = EvaluationScore(
            evaluation_task_id=evaluation_task_id,
            execution_result_id=execution_result_id,
            evaluator_type=evaluator_type,
            judge_provider_id=judge_provider_id,
            judge_model=judge_model,
            score=score,
            dimension_scores_json=dimension_scores_json,
            verdict=verdict,
            reasoning_summary=reasoning_summary,
            raw_judge_response_json=raw_judge_response_json,
        )
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def list_scores(self, task_id: int) -> list[EvaluationScore]:
        return (
            self.session.query(EvaluationScore)
            .filter(EvaluationScore.evaluation_task_id == task_id)
            .order_by(EvaluationScore.id.asc())
            .all()
        )

    def can_delete_task(self, task_id: int) -> bool:
        task = self.get_task(task_id)
        if task is None:
            return False
        if task.status != "pending":
            return False
        if task.progress_total > 0 or task.progress_done > 0:
            return False
        score_count = self.session.query(EvaluationScore).filter(EvaluationScore.evaluation_task_id == task_id).count()
        return score_count == 0

    def delete_task(self, task_id: int) -> bool:
        task = self.get_task(task_id)
        if task is None:
            return False
        self.session.delete(task)
        self.session.flush()
        return True

    def delete_scores(self, task_id: int) -> None:
        self.session.query(EvaluationScore).filter(EvaluationScore.evaluation_task_id == task_id).delete()
        self.session.flush()
