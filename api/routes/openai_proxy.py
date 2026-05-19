from fastapi import APIRouter
from fastapi import Body

from api.services.proxy_service import ProxyService


router = APIRouter(prefix="/v1", tags=["openai-proxy"])


def get_proxy_service() -> ProxyService:
    return ProxyService()


@router.post("/chat/completions")
def chat_completions(payload: dict = Body(...)) -> dict:
    service = get_proxy_service()
    return service.handle_chat_completions(payload)
