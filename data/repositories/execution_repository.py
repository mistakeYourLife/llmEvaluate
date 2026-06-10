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

    def update_task_name(self, task_id: int, name: str) -> ExecutionTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        task.name = name.strip() or str(task.id)
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def update_status(self, task_id: int, status: str) -> ExecutionTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        task.status = status
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def update_progress(self, task_id: int, *, total: int, done: int) -> ExecutionTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        task.progress_total = total
        task.progress_done = done
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def create_result(
        self,
        *,
        execution_task_id: int,
        source_request_id: int | None,
        sample_id: int | None,
        provider_id: int,
        model: str | None,
        run_index: int,
        request_body_json: dict,
        response_body_json: dict,
        output_text: str | None,
        http_status: int | None,
        success: bool,
        first_token_latency_ms: int | None = None,
        complete_latency_ms: int | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        tokens_per_second: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> ExecutionResult:
        result = ExecutionResult(
            execution_task_id=execution_task_id,
            source_request_id=source_request_id,
            sample_id=sample_id,
            provider_id=provider_id,
            model=model,
            run_index=run_index,
            request_body_json=request_body_json,
            response_body_json=response_body_json,
            output_text=output_text,
            http_status=http_status,
            first_token_latency_ms=first_token_latency_ms,
            complete_latency_ms=complete_latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            tokens_per_second=tokens_per_second,
            success=success,
            error_code=error_code,
            error_message=error_message,
        )
        self.session.add(result)
        self.session.flush()
        self.session.refresh(result)
        return result

    def list_results(self, task_id: int) -> list[ExecutionResult]:
        return (
            self.session.query(ExecutionResult)
            .filter(ExecutionResult.execution_task_id == task_id)
            .order_by(ExecutionResult.id.asc())
            .all()
        )

    def get_result(self, result_id: int) -> ExecutionResult | None:
        return self.session.get(ExecutionResult, result_id)

    def delete_results(self, task_id: int) -> None:
        self.session.query(ExecutionResult).filter(ExecutionResult.execution_task_id == task_id).delete()
        self.session.flush()
