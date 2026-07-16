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

    # Lấy token đầu tiên và bỏ hậu tố "@botname" — Telegram thường gửi "/reset@ten_bot"
    # khi lệnh được chọn từ menu command (đặc biệt trong group chat), nên so sánh
    # nguyên văn "== '/reset'" sẽ KHÔNG khớp và lệnh bị rơi xuống luồng chat bình thường.
    raw = std_msg.message.strip()
    cmd = raw.split()[0].lower().split("@")[0] if raw else ""
    if cmd == "/start":
        await adapter.on_start_command(std_msg.sender_id)
        return
    if cmd == "/reset":
        # Xóa thật checkpoint LangGraph của đúng session này trước khi báo cho khách —
        # trước đây on_reset_command chỉ gửi tin nhắn xác nhận mà không xóa gì cả.
        await _chat_service.reset_session(std_msg.session_key)
        await adapter.on_reset_command(std_msg.sender_id)
        return

    await adapter.send_typing(std_msg.sender_id)

    request = ChatRequest(
        message=std_msg.message,
        session_id=std_msg.session_key,
        channel=platform,
    )
    response = await _chat_service.handle_chat(request)
    reply_text = response.response or (
        "Xin lỗi, hiện tại Pancharm chưa tìm được thông tin phù hợp với yêu cầu của bạn. "
        "Bạn có thể mô tả thêm hoặc thử câu hỏi khác nhé! 🙏"
    )
    await adapter.send_message(std_msg.sender_id, reply_text)

    # Gửi ảnh sản phẩm SAU tin nhắn text — response.image_urls chỉ có dữ liệu khi khách
    # yêu cầu xem ảnh ở lượt này (xem ChatService._resolve_product_images)
    if response.image_urls:
        await adapter.send_photos(std_msg.sender_id, response.image_urls)

    custom_logger.info(
        f"[handler] done | {platform}:{bot_name} | "
        f"sender={std_msg.sender_id} | "
        f"psych={response.psych_state} | iter={response.iteration_count}"
    )
