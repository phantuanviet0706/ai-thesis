import hashlib
import hmac
from typing import Any, Optional

import httpx

from adapter.base_adapter import BaseAdapter
from core.config import settings
from core.logger import custom_logger
from schemas.standard_message import StandardMessage

_ZALO_API = "https://openapi.zalo.me/v3.0/oa"


class ZaloAdapter(BaseAdapter):

    @property
    def platform(self) -> str:
        return "zalo"

    @property
    def bot_name(self) -> str:
        return "pancharm"

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def register(self) -> None:
        """Zalo OA webhook setup được cấu hình trên Zalo Developer Portal."""
        custom_logger.info("[ZaloAdapter] register() — no-op (manual setup on Zalo Portal)")

    # ── Security ─────────────────────────────────────────────────────────────

    def verify_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool:
        """Xác thực X-ZEvent-Signature: HMAC-SHA256 của raw body với app_secret."""
        if not settings.ZALO_APP_SECRET:
            return True
        sig = headers.get("x-zevent-signature", "")
        expected = hmac.new(
            settings.ZALO_APP_SECRET.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(sig, expected)

    # ── Message I/O ──────────────────────────────────────────────────────────

    def parse_request(self, payload: dict[str, Any]) -> Optional[StandardMessage]:
        """
        Parse Zalo OA webhook payload → StandardMessage.
        Chỉ xử lý event_name = "user_send_text".
        """
        if payload.get("event_name") != "user_send_text":
            return None

        text: str = payload.get("message", {}).get("text", "").strip()
        if not text:
            return None

        sender_id = str(payload.get("sender", {}).get("id", ""))
        if not sender_id:
            return None

        return StandardMessage(
            platform=self.platform,
            bot_name=self.bot_name,
            sender_id=sender_id,
            session_key=self.make_session_key(sender_id),
            message=text,
            raw_payload=payload,
            metadata={
                "msg_id": payload.get("message", {}).get("msg_id"),
                "is_command": text.startswith("/"),
            },
        )

    async def send_message(self, receiver_id: str, message: str, **kwargs) -> None:
        await self._call_api("message/cs", {
            "recipient": {"user_id": receiver_id},
            "message": {"text": message},
        })

    async def send_typing(self, receiver_id: str) -> None:
        """Zalo OA không hỗ trợ typing indicator — no-op."""

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

    async def _call_api(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        url = f"{_ZALO_API}/{endpoint}"
        headers = {
            "access_token": settings.ZALO_OA_ACCESS_TOKEN,
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=data, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            custom_logger.error(
                f"[ZaloAdapter] API error | endpoint={endpoint} | "
                f"status={exc.response.status_code} | detail={exc.response.text[:300]}"
            )
            raise
        except httpx.RequestError as exc:
            custom_logger.error(f"[ZaloAdapter] request failed | endpoint={endpoint} | error={exc}")
            raise
