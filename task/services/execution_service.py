from sqlalchemy.orm import Session

from data.models import ExecutionTask
from data.repositories.execution_repository import ExecutionRepository


class ExecutionService:
    def __init__(self, session: Session):
        self.repository = ExecutionRepository(session)

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
        return self.repository.create_task(
            name=name,
            source_type=source_type,
            source_ref_id=source_ref_id,
            target_provider_ids_json=target_provider_ids_json,
            target_models_json=target_models_json,
            task_config_json=task_config_json,
        )

    def list_tasks(self) -> list[ExecutionTask]:
        return self.repository.list_tasks()

    def get_task(self, task_id: int) -> ExecutionTask | None:
        return self.repository.get_task(task_id)

    def start_task(self, task_id: int) -> ExecutionTask | None:
        return self.repository.update_status(task_id, "running")

    def stop_task(self, task_id: int) -> ExecutionTask | None:
        return self.repository.update_status(task_id, "stopped")

    def retry_task(self, task_id: int) -> ExecutionTask | None:
        return self.repository.update_status(task_id, "pending")
