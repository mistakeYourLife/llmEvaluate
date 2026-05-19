from sqlalchemy.orm import Session

from data.models import ExecutionResult
from data.models import ExecutionTask


class ExecutionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_task(
        self,
        *,
        name: str,
        source_type: str,
        source_ref_id: int,
        target_provider_ids_json: dict,
        target_models_json: dict,
        task_config_json: dict,
    ) -> ExecutionTask:
        task = ExecutionTask(
            name=name,
            source_type=source_type,
            source_ref_id=source_ref_id,
            target_provider_ids_json=target_provider_ids_json,
            target_models_json=target_models_json,
            status="pending",
            progress_total=0,
            progress_done=0,
            task_config_json=task_config_json,
        )
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def list_tasks(self) -> list[ExecutionTask]:
        return self.session.query(ExecutionTask).order_by(ExecutionTask.id.desc()).all()

    def get_task(self, task_id: int) -> ExecutionTask | None:
        return self.session.get(ExecutionTask, task_id)

    def update_status(self, task_id: int, status: str) -> ExecutionTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        task.status = status
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def list_results(self, task_id: int) -> list[ExecutionResult]:
        return (
            self.session.query(ExecutionResult)
            .filter(ExecutionResult.execution_task_id == task_id)
            .order_by(ExecutionResult.id.asc())
            .all()
        )
