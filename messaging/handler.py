"""
handle_message() — logic xử lý tin nhắn dùng chung cho cả hai luồng:
  1. Kafka consumer  (BotMessageConsumer._dispatch)
  2. Direct fallback (BackgroundTasks khi Kafka chưa sẵn sàng)

Tách ra file riêng để tránh circular import và dễ unit test.
"""

from core.logger import custom_logger
from adapter.registry import AdapterRegistry
from schemas.chat_schema import ChatRequest
from schemas.standard_message import StandardMessage
from services.chat_service import ChatService

_chat_service = ChatService()


async def handle_message(std_msg: StandardMessage) -> None:
    """
    Xử lý một StandardMessage:
      - Tra adapter từ registry
      - Xử lý command /start, /reset
      - Gửi typing indicator
      - Gọi MAS pipeline (ChatService)
      - Gửi phản hồi về platform
    """
    platform = std_msg.platform
    bot_name = std_msg.bot_name

    adapter = AdapterRegistry.get(platform, bot_name)
    if not adapter:
        custom_logger.warning(
            f"[handler] no adapter for {platform}:{bot_name} — skipping"
        )
        return

    cmd = std_msg.message.strip().lower()
    if cmd == "/start":
        await adapter.on_start_command(std_msg.sender_id)
        return
    if cmd == "/reset":
        await adapter.on_reset_command(std_msg.sender_id)
        return

    await adapter.send_typing(std_msg.sender_id)

    request = ChatRequest(
        message=std_msg.message,
        session_id=std_msg.session_key,
        channel=platform,
    )
    response = await _chat_service.handle_chat(request)
    await adapter.send_message(std_msg.sender_id, response.response)

    custom_logger.info(
        f"[handler] done | {platform}:{bot_name} | "
        f"sender={std_msg.sender_id} | "
        f"psych={response.psych_state} | iter={response.iteration_count}"
    )
