from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from api.providers.base import build_provider_adapter
from admin.schemas import ProviderCreateRequest
from admin.schemas import ProviderListResponse
from admin.schemas import ProviderProbeResponse
from admin.schemas import ProviderResponse
from admin.schemas import ProviderUpdateRequest
from data.db import get_db_session
from data.repositories.provider_repository import ProviderRepository


router = APIRouter(prefix="/admin/providers", tags=["providers"])


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
def create_provider(
    payload: ProviderCreateRequest,
    session: Session = Depends(get_db_session),
) -> ProviderResponse:
    repository = ProviderRepository(session)
    provider = repository.create(
        name=payload.name,
        code=payload.code,
        provider_type=payload.provider_type,
        base_url=payload.base_url,
        api_key=payload.api_key,
        default_model=payload.default_model,
    )
    return ProviderResponse.model_validate(provider)


@router.get("", response_model=ProviderListResponse)
def list_providers(session: Session = Depends(get_db_session)) -> ProviderListResponse:
    repository = ProviderRepository(session)
    return ProviderListResponse(items=[ProviderResponse.model_validate(item) for item in repository.list_all()])


@router.put("/{provider_id}", response_model=ProviderResponse)
def update_provider(
    provider_id: int,
    payload: ProviderUpdateRequest,
    session: Session = Depends(get_db_session),
) -> ProviderResponse:
    repository = ProviderRepository(session)
    provider = repository.update(
        provider_id,
        name=payload.name,
        base_url=payload.base_url,
        default_model=payload.default_model,
    )
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    return ProviderResponse.model_validate(provider)


@router.post("/{provider_id}/disable", response_model=ProviderResponse)
def disable_provider(
    provider_id: int,
    session: Session = Depends(get_db_session),
) -> ProviderResponse:
    repository = ProviderRepository(session)
    provider = repository.set_enabled(provider_id, enabled=False)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    return ProviderResponse.model_validate(provider)


@router.post("/{provider_id}/enable", response_model=ProviderResponse)
def enable_provider(
    provider_id: int,
    session: Session = Depends(get_db_session),
) -> ProviderResponse:
    repository = ProviderRepository(session)
    provider = repository.set_enabled(provider_id, enabled=True)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    return ProviderResponse.model_validate(provider)


@router.post("/{provider_id}/test", response_model=ProviderProbeResponse)
def test_provider_connection(
    provider_id: int,
    session: Session = Depends(get_db_session),
) -> ProviderProbeResponse:
    repository = ProviderRepository(session)
    provider = repository.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    adapter = build_provider_adapter(provider)
    result = adapter.probe()
    return ProviderProbeResponse(ok=result.ok, detail=result.detail)
