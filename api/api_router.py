from fastapi import APIRouter

from api.v1.endpoints.base import auth_controller, chat_controller, sample_controller
from api.v1.endpoints.webhook import webhook_controller

api_router = APIRouter()

api_router.include_router(
    auth_controller.router,
    prefix="/auth",
    tags=["Auth"],
)

api_router.include_router(
    chat_controller.router,
    prefix="/chat",
    tags=["Chat"],
)

api_router.include_router(
    sample_controller.router,
    prefix="/sample",
    tags=["Sample Data"],
)

api_router.include_router(
    webhook_controller.router,
    prefix="/webhook",
    tags=["Webhook"],
)
