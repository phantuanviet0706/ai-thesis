from fastapi import APIRouter

from api.chat_router import chat_router

api_router = APIRouter()
api_router.include_router(chat_router)
