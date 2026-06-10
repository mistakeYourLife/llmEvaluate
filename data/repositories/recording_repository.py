from sqlalchemy.orm import Session

from data.models import ExecutionResult
from data.models import ExecutionTask
from data.models import RecordedRequest
from data.models import RecordedResponse
from data.schemas.recording import RecordedRequestCreate
from data.schemas.recording import RecordedResponseCreate


class RecordingRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_request(self, payload: RecordedRequestCreate) -> RecordedRequest:
        request = RecordedRequest(**payload.model_dump())
        self.session.add(request)
        self.session.flush()
        if request.name is None or not request.name.strip():
            request.name = str(request.id)
            self.session.flush()
        self.session.refresh(request)
        return request

    def create_response(self, payload: RecordedResponseCreate) -> RecordedResponse:
        response = RecordedResponse(**payload.model_dump())
        self.session.add(response)
        self.session.flush()
        self.session.refresh(response)
        return response

    def list_records(self, provider_id: int | None = None) -> list[tuple[RecordedRequest, RecordedResponse | None]]:
        query = (
            self.session.query(RecordedRequest, RecordedResponse)
            .outerjoin(RecordedResponse, RecordedResponse.request_id == RecordedRequest.id)
            .order_by(RecordedRequest.id.desc())
        )
        if provider_id is not None:
            query = query.filter(RecordedRequest.provider_id == provider_id)
        return query.all()

    def get_record(self, request_id: int) -> tuple[RecordedRequest, RecordedResponse | None] | None:
        return (
            self.session.query(RecordedRequest, RecordedResponse)
            .outerjoin(RecordedResponse, RecordedResponse.request_id == RecordedRequest.id)
            .filter(RecordedRequest.id == request_id)
            .one_or_none()
        )

    def update_record_name(self, request_id: int, name: str) -> tuple[RecordedRequest, RecordedResponse | None] | None:
        record = self.get_record(request_id)
        if record is None:
            return None

        request, _ = record
        request.name = name.strip() or str(request.id)
        self.session.flush()
        self.session.refresh(request)
        return self.get_record(request_id)

    def get_delete_blocker(self, request_id: int) -> str | None:
        execution_task_count = (
            self.session.query(ExecutionTask)
            .filter(
                ExecutionTask.source_type == "recorded_request",
                ExecutionTask.source_ref_id == request_id,
            )
            .count()
        )
        if execution_task_count > 0:
            return f"该录制样本已关联 {execution_task_count} 条执行任务，暂不允许删除。"

        execution_result_count = (
            self.session.query(ExecutionResult).filter(ExecutionResult.source_request_id == request_id).count()
        )
        if execution_result_count > 0:
            return f"该录制样本已关联 {execution_result_count} 条执行结果，暂不允许删除。"

        return None

    def delete_record(self, request_id: int) -> bool:
        record = self.get_record(request_id)
        if record is None:
            return False

        request, response = record
        if response is not None:
            self.session.delete(response)
            self.session.flush()
        self.session.delete(request)
        self.session.flush()
        return True
