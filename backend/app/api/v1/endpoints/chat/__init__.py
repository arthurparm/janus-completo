from fastapi import APIRouter

from .chat_admin import router as chat_admin_router
from .chat_history import router as chat_history_router
from .chat_message import router as chat_message_router
from .chat_stream import router as chat_stream_router

router = APIRouter(tags=["Chat"])
router.include_router(chat_message_router)
router.include_router(chat_history_router)
router.include_router(chat_stream_router)
router.include_router(chat_admin_router)

__all__ = ["router"]
