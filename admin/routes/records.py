from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlalchemy.orm import Session

from admin.schemas import RecordItemResponse
from admin.schemas import RecordListResponse
from data.db import get_db_session
from data.repositories.recording_repository import RecordingRepository


router = APIRouter(prefix="/admin/records", tags=["records"])


def _to_record_item(record_pair: tuple) -> RecordItemResponse:
    request, response = record_pair
    return RecordItemResponse(
        id=request.id,
        provider_id=request.provider_id,
        request_type=request.request_type,
        model=request.model,
        is_stream=request.is_stream,
        http_status=response.http_status if response else None,
        response_id=response.id if response else None,
    )


@router.get("", response_model=RecordListResponse)
def list_records(
    provider_id: int | None = Query(default=None),
    session: Session = Depends(get_db_session),
) -> RecordListResponse:
    repository = RecordingRepository(session)
    items = [_to_record_item(item) for item in repository.list_records(provider_id=provider_id)]
    return RecordListResponse(items=items)


@router.get("/{request_id}", response_model=RecordItemResponse)
def get_record(
    request_id: int,
    session: Session = Depends(get_db_session),
) -> RecordItemResponse:
    repository = RecordingRepository(session)
    record = repository.get_record(request_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return _to_record_item(record)
