from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from sqlalchemy.orm import Session

from api.services.proxy_service import ProxyService
from data.db import get_db_session


router = APIRouter(prefix="/v1", tags=["openai-proxy"])


def get_proxy_service() -> ProxyService:
    return ProxyService()


@router.post("/chat/completions")
def chat_completions(
    payload: dict = Body(...),
    session: Session = Depends(get_db_session),
) -> dict:
    service = ProxyService(session)
    return service.handle_chat_completions(payload)
