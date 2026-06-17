import hmac
from typing import Any, Optional

import httpx

from adapter.base_adapter import BaseAdapter
from core.config import settings
from core.logger import custom_logger
from schemas.standard_message import StandardMessage

_MAX_MSG_LEN = 4096


class TelegramAdapter(BaseAdapter):

    @property
    def platform(self) -> str:
        return "telegram"

    @property
    def bot_name(self) -> str:
        return "pancharm"

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def register(self) -> None:
        if not settings.TELEGRAM_WEBHOOK_BASE_URL:
            custom_logger.warning("[TelegramAdapter] TELEGRAM_WEBHOOK_BASE_URL chưa cấu hình — bỏ qua")
            return
        webhook_url = (
            f"{settings.TELEGRAM_WEBHOOK_BASE_URL.rstrip('/')}"
            f"/api/v1/webhook/telegram/pancharm"
        )
        result = await self._call_api("setWebhook", {
            "url": webhook_url,
            "secret_token": settings.TELEGRAM_WEBHOOK_SECRET,
            "allowed_updates": ["message"],
        })
        custom_logger.info(f"[TelegramAdapter] webhook registered | url={webhook_url} | ok={result.get('ok')}")

    # ── Security ─────────────────────────────────────────────────────────────

    def verify_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool:
        if not settings.TELEGRAM_WEBHOOK_SECRET:
            return True
        incoming = headers.get("x-telegram-bot-api-secret-token", "")
        return hmac.compare_digest(incoming, settings.TELEGRAM_WEBHOOK_SECRET)

    # ── Message I/O ──────────────────────────────────────────────────────────

    def parse_request(self, payload: dict[str, Any]) -> Optional[StandardMessage]:
        msg = payload.get("message") or payload.get("edited_message")
        if not msg:
            return None
        text: str = msg.get("text", "").strip()
        if not text:
            return None
        sender = msg.get("from", {})
        chat_id = str(msg.get("chat", {}).get("id", sender.get("id", "")))
        return StandardMessage(
            platform=self.platform,
            bot_name=self.bot_name,
            sender_id=chat_id,
            session_key=self.make_session_key(chat_id),
            message=text,
            raw_payload=payload,
            metadata={
                "username": sender.get("username"),
                "first_name": sender.get("first_name"),
                "message_id": msg.get("message_id"),
                "is_command": text.startswith("/"),
            },
        )

    async def send_message(self, receiver_id: str, message: str, **kwargs) -> None:
        for chunk in _split(message):
            await self._call_api("sendMessage", {
                "chat_id": receiver_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            })

    async def send_typing(self, receiver_id: str) -> None:
        await self._call_api("sendChatAction", {"chat_id": receiver_id, "action": "typing"})

    async def on_start_command(self, receiver_id: str) -> None:
        await self.send_message(
            receiver_id,
            "Xin chào! Mình là tư vấn viên AI của Pancharm — "
            "thương hiệu trang sức phong thủy Việt Nam. "
            "Bạn muốn tìm trang sức gì hôm nay?",
        )

    async def on_reset_command(self, receiver_id: str) -> None:
        await self.send_message(receiver_id, "Đã reset hội thoại. Mình có thể giúp gì cho bạn?")

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _call_api(self, method: str, data: dict[str, Any]) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=data)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            custom_logger.error(
                f"[TelegramAdapter] API error | method={method} | "
                f"status={exc.response.status_code} | detail={exc.response.text[:300]}"
            )
            raise
        except httpx.RequestError as exc:
            custom_logger.error(f"[TelegramAdapter] request failed | method={method} | error={exc}")
            raise


def _split(text: str) -> list[str]:
    """Chia tin nhắn tại ranh giới đoạn để không vượt giới hạn 4096 ký tự của Telegram."""
    if len(text) <= _MAX_MSG_LEN:
        return [text]
    chunks: list[str] = []
    current = ""
    for para in text.split("\n\n"):
        candidate = (current + "\n\n" + para).lstrip() if current else para
        if len(candidate) > _MAX_MSG_LEN:
            if current.strip():
                chunks.append(current.strip())
            current = para
        else:
            current = candidate
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text[:_MAX_MSG_LEN]]
