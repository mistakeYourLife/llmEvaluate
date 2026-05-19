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
