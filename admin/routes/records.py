from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Response
from fastapi import status
from sqlalchemy.orm import Session

from admin.schemas import RecordDetailResponse
from admin.schemas import RecordItemResponse
from admin.schemas import RecordListResponse
from admin.schemas import RecordResponseDetailResponse
from admin.schemas import RecordUpdateRequest
from data.db import get_db_session
from data.repositories.recording_repository import RecordingRepository


router = APIRouter(prefix="/admin/records", tags=["records"])


def _resolve_record_name(request) -> str:
    if request.name is not None and request.name.strip():
        return request.name.strip()
    return str(request.id)


def _to_record_item(record_pair: tuple) -> RecordItemResponse:
    request, response = record_pair
    return RecordItemResponse(
        id=request.id,
        name=_resolve_record_name(request),
        provider_id=request.provider_id,
        request_type=request.request_type,
        model=request.model,
        is_stream=request.is_stream,
        http_status=response.http_status if response else None,
        response_id=response.id if response else None,
        error_message=response.error_message if response else None,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


def _to_record_detail(record_pair: tuple) -> RecordDetailResponse:
    request, response = record_pair
    return RecordDetailResponse(
        **_to_record_item(record_pair).model_dump(),
        source_app=request.source_app,
        request_headers_json=request.request_headers_json,
        request_body_json=request.request_body_json,
        request_text_snapshot=request.request_text_snapshot,
        response=RecordResponseDetailResponse(
            id=response.id if response else None,
            http_status=response.http_status if response else None,
            response_headers_json=response.response_headers_json if response else {},
            response_body_json=response.response_body_json if response else {},
            response_text_snapshot=response.response_text_snapshot if response else None,
            first_token_latency_ms=response.first_token_latency_ms if response else None,
            complete_latency_ms=response.complete_latency_ms if response else None,
            prompt_tokens=response.prompt_tokens if response else None,
            completion_tokens=response.completion_tokens if response else None,
            total_tokens=response.total_tokens if response else None,
            tokens_per_second=response.tokens_per_second if response else None,
            error_code=response.error_code if response else None,
            error_message=response.error_message if response else None,
            created_at=response.created_at if response else None,
            updated_at=response.updated_at if response else None,
        ),
    )


@router.get("", response_model=RecordListResponse)
def list_records(
    provider_id: int | None = Query(default=None),
    session: Session = Depends(get_db_session),
) -> RecordListResponse:
    repository = RecordingRepository(session)
    items = [_to_record_item(item) for item in repository.list_records(provider_id=provider_id)]
    return RecordListResponse(items=items)


@router.get("/{request_id}", response_model=RecordDetailResponse)
def get_record(
    request_id: int,
    session: Session = Depends(get_db_session),
) -> RecordDetailResponse:
    repository = RecordingRepository(session)
    record = repository.get_record(request_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return _to_record_detail(record)


@router.put("/{request_id}", response_model=RecordDetailResponse)
def update_record(
    request_id: int,
    payload: RecordUpdateRequest,
    session: Session = Depends(get_db_session),
) -> RecordDetailResponse:
    repository = RecordingRepository(session)
    record = repository.update_record_name(request_id, payload.name)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return _to_record_detail(record)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    request_id: int,
    session: Session = Depends(get_db_session),
) -> Response:
    repository = RecordingRepository(session)
    record = repository.get_record(request_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    blocker = repository.get_delete_blocker(request_id)
    if blocker is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=blocker)

    repository.delete_record(request_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
