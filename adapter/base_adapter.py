"""
BaseAdapter — contract duy nhất mà mọi platform adapter phải thực hiện.

Không chứa logic, không chứa config — chỉ khai báo interface.
Mỗi [platform]_adapter.py tự implement đầy đủ 5 phương thức bắt buộc
và 2 hook tùy chọn (on_start_command, on_reset_command).
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from schemas.standard_message import StandardMessage


class BaseAdapter(ABC):

    # ── Identity ─────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def platform(self) -> str:
        """Tên platform — phải khớp với giá trị ChatRequest.channel."""

    @property
    @abstractmethod
    def bot_name(self) -> str:
        """Tên logic của bot instance — phân biệt nhiều bot trên cùng platform."""

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @abstractmethod
    async def register(self) -> None:
        """
        Đăng ký bot với platform (gọi khi app khởi động).
        Ví dụ: Telegram → setWebhook, Zalo → đăng ký OA webhook URL.
        """

    # ── Security ─────────────────────────────────────────────────────────────

    @abstractmethod
    def verify_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool:
        """
        Xác thực tính hợp lệ của webhook request.
        Ví dụ: Telegram → kiểm tra X-Telegram-Bot-Api-Secret-Token header.
        """

    # ── Message I/O ──────────────────────────────────────────────────────────

    @abstractmethod
    def parse_request(self, payload: dict[str, Any]) -> Optional[StandardMessage]:
        """
        Chuẩn hóa raw webhook payload → StandardMessage.
        Trả về None nếu payload không phải tin nhắn text của người dùng
        (ví dụ: sticker, ảnh, callback query, system event).
        """

    @abstractmethod
    async def send_message(self, receiver_id: str, message: str, **kwargs) -> None:
        """Gửi phản hồi text về cho người dùng trên platform."""

    @abstractmethod
    async def send_typing(self, receiver_id: str) -> None:
        """
        Gửi trạng thái 'đang nhập' để cải thiện UX trong khi MAS xử lý.
        Không phải platform nào cũng hỗ trợ — implement no-op nếu không có.
        """

    async def send_photos(self, receiver_id: str, photo_urls: list[str], caption: str | None = None) -> None:
        """
        Gửi 1 hoặc nhiều ảnh sản phẩm cho khách (dùng khi ChatResponse.image_urls có dữ liệu,
        xem services/chat_service.py::_resolve_product_images). Mặc định no-op — override ở
        adapter nào hỗ trợ gửi ảnh. Không phải @abstractmethod vì không phải platform nào
        cũng cần/hỗ trợ tính năng này ngay từ đầu.
        """

    # ── Optional hooks ────────────────────────────────────────────────────────

    async def on_start_command(self, receiver_id: str) -> None:
        """Xử lý lệnh /start — override để gửi tin nhắn chào mừng tùy chỉnh."""

    async def on_reset_command(self, receiver_id: str) -> None:
        """
        Gửi xác nhận cho khách sau lệnh /reset — override để tùy chỉnh nội dung.
        Việc xóa checkpoint LangGraph thật sự đã được messaging/handler.py thực hiện
        (ChatService.reset_session) TRƯỚC khi hook này được gọi — không cần tự xóa lại ở đây.
        """

    # ── Utility ───────────────────────────────────────────────────────────────

    def make_session_key(self, sender_id: str) -> str:
        """
        Tạo session key duy nhất toàn cục dùng làm LangGraph thread_id.
        Format: "{platform}:{bot_name}:{sender_id}"
        Ví dụ: "telegram:pancharm:123456789"
        """
        return f"{self.platform}:{self.bot_name}:{sender_id}"
