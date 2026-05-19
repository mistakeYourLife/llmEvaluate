from sqlalchemy.orm import Session

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
