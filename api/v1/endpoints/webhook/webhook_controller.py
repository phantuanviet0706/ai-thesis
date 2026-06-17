"""
Generic webhook controller — một endpoint duy nhất cho mọi platform/bot.

Route:
  POST /api/v1/webhook/{platform}/{bot_name}   — nhận tin nhắn từ platform
  GET  /api/v1/webhook/bots                    — danh sách bot đã đăng ký (debug)

Chế độ xử lý (tự động chọn):
  [Kafka sẵn sàng]  → publish StandardMessage lên Kafka → Consumer xử lý async
  [Kafka chưa sẵn]  → BackgroundTask xử lý trực tiếp    → tiện cho dev/test

Telegram example:
  POST /api/v1/webhook/telegram/pancharm
  Body: Telegram Update JSON (update_id, message.text, message.chat.id, ...)
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from adapter.registry import AdapterRegistry
from core.config import settings
from core.logger import custom_logger
from messaging.handler import handle_message
from messaging.producer import bot_producer

router = APIRouter()


@router.get("/bots", summary="List registered bots")
async def list_bots() -> dict:
    """Trả về danh sách các bot đã đăng ký — dùng để debug và xác nhận setup."""
    registered = AdapterRegistry.list_registered()
    return {
        "count": len(registered),
        "bots": registered,
        "kafka_ready": bot_producer.is_ready,
    }


@router.get(
    "/messenger/{bot_name}",
    summary="Facebook Messenger webhook verification",
    include_in_schema=False,
)
async def verify_messenger_webhook(bot_name: str, request: Request) -> PlainTextResponse:
    """
    Facebook gọi GET này khi setup webhook trên Developer Portal.
    Phải trả về hub.challenge nếu hub.verify_token khớp MESSENGER_VERIFY_TOKEN.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge", "")
    if mode == "subscribe" and token == settings.MESSENGER_VERIFY_TOKEN:
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verify token mismatch.")


@router.post(
    "/{platform}/{bot_name}",
    status_code=status.HTTP_200_OK,
    summary="Receive webhook from platform",
)
async def handle_webhook(
    platform: str,
    bot_name: str,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Nhận webhook từ platform, xác thực, sau đó:
      - Nếu Kafka sẵn sàng → publish (xử lý async bởi consumer)
      - Nếu không          → BackgroundTask (xử lý trực tiếp, tiện test)
    Luôn trả về 200 OK ngay để platform không timeout.
    """
    adapter = AdapterRegistry.get(platform, bot_name)
    if not adapter:
        custom_logger.warning(
            f"[WebhookController] unknown bot | platform={platform} | bot={bot_name}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot '{bot_name}' not registered on platform '{platform}'. "
                   f"Check adapter/setup.py and .env config.",
        )

    raw_body = await request.body()
    headers = dict(request.headers)

    if not adapter.verify_webhook(headers, raw_body):
        custom_logger.warning(
            f"[WebhookController] auth failed | platform={platform} | bot={bot_name}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook secret token mismatch.",
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be valid JSON.",
        )

    std_msg = adapter.parse_request(payload)
    if std_msg is None:
        return {"ok": True, "skipped": True, "reason": "non-text update"}

    if bot_producer.is_ready:
        await bot_producer.publish(std_msg)
        mode = "kafka"
    else:
        background_tasks.add_task(handle_message, std_msg)
        mode = "direct"

    custom_logger.info(
        f"[WebhookController] accepted | platform={platform} | bot={bot_name} | "
        f"sender={std_msg.sender_id} | mode={mode} | "
        f"msg='{std_msg.message[:60]}'"
    )

    return {"ok": True, "mode": mode, "session": std_msg.session_key}
