"""
handle_message() — logic xử lý tin nhắn dùng chung cho cả hai luồng:
  1. Kafka consumer  (BotMessageConsumer._dispatch)
  2. Direct fallback (BackgroundTasks khi Kafka chưa sẵn sàng)

Tin nhắn text (không phải command) được đưa qua MessageDebouncer (xem messaging/debouncer.py) —
gộp nhiều tin nhắn liên tiếp của cùng khách trong MESSAGE_DEBOUNCE_SECONDS thành 1 lượt xử lý duy
nhất, tránh khách gõ rời rạc nhiều tin ngắn ("cho hỏi"/"vòng tay"/"mệnh kim"/"tầm 2 triệu") khiến
hệ thống chạy graph + trả lời riêng cho từng tin một, gây rối/chồng chéo phản hồi.

Tách ra file riêng để tránh circular import và dễ unit test.
"""

from core.logger import custom_logger
from adapter.registry import AdapterRegistry
from messaging.debouncer import message_debouncer
from schemas.chat_schema import ChatRequest
from schemas.standard_message import StandardMessage
from services.chat_service import ChatService

_chat_service = ChatService()


async def handle_message(std_msg: StandardMessage) -> None:
    """
    Xử lý một StandardMessage:
      - Tra adapter từ registry
      - Xử lý command /start, /reset — NGAY LẬP TỨC, không qua debounce (lệnh điều khiển cần
        phản hồi tức thời, không phải 1 phần của "block" câu hỏi cần gộp)
      - Gửi typing indicator
      - Đưa tin nhắn vào MessageDebouncer — pipeline + trả lời thật sự chỉ chạy trong
        _process_combined_message(), sau khi khách ngừng gửi tin trong đủ MESSAGE_DEBOUNCE_SECONDS
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

    # Gửi typing cho MỖI tin nhắn tới (kể cả tin sẽ bị gộp) — giữ hiệu ứng "đang nhập" liên
    # tục trong lúc khách còn đang gõ tiếp, thay vì tắt rồi bật lại giữa các tin trong 1 block.
    await adapter.send_typing(std_msg.sender_id)
    await message_debouncer.add(std_msg, on_flush=_process_combined_message)


async def _process_combined_message(std_msg: StandardMessage) -> None:
    """
    @desc Callback MessageDebouncer gọi đúng 1 lần sau khi khách ngừng gửi tin trong đủ
    MESSAGE_DEBOUNCE_SECONDS — std_msg.message lúc này là nội dung đã GỘP của mọi tin nhắn liên
    tiếp trong block, chạy MAS pipeline và trả lời đúng 1 lần cho cả block.
    @params std_msg (StandardMessage): Tin nhắn đã gộp (session_key/sender_id giữ nguyên, message đã nối)
    """
    platform = std_msg.platform
    adapter = AdapterRegistry.get(platform, std_msg.bot_name)
    if not adapter:
        custom_logger.warning(
            f"[handler] no adapter for {platform}:{std_msg.bot_name} on flush — skipping"
        )
        return

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
        f"[handler] done | {platform}:{std_msg.bot_name} | "
        f"sender={std_msg.sender_id} | "
        f"psych={response.psych_state} | iter={response.iteration_count}"
    )
