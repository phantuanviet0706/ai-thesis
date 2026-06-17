import hashlib
import hmac
from typing import Any, Optional

import httpx

from adapter.base_adapter import BaseAdapter
from core.config import settings
from core.logger import custom_logger
from schemas.standard_message import StandardMessage

_GRAPH_API = "https://graph.facebook.com/v19.0"


class MessengerAdapter(BaseAdapter):

    @property
    def platform(self) -> str:
        return "messenger"

    @property
    def bot_name(self) -> str:
        return "pancharm"

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def register(self) -> None:
        """Messenger webhook setup được thực hiện thủ công trên Facebook Developer Portal."""
        custom_logger.info("[MessengerAdapter] register() — no-op (manual setup on Facebook Portal)")

    # ── Security ─────────────────────────────────────────────────────────────

    def verify_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool:
        """Xác thực X-Hub-Signature-256: sha256=HMAC(body, app_secret)."""
        if not settings.MESSENGER_APP_SECRET:
            return True
        sig = headers.get("x-hub-signature-256", "")
        if not sig.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(
            settings.MESSENGER_APP_SECRET.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(sig, expected)

    # ── Message I/O ──────────────────────────────────────────────────────────

    def parse_request(self, payload: dict[str, Any]) -> Optional[StandardMessage]:
        """
        Parse Facebook Messenger webhook payload → StandardMessage.
        Chỉ xử lý text message, bỏ qua quick replies, postback, sticker, v.v.
        """
        if payload.get("object") != "page":
            return None
        try:
            event = payload["entry"][0]["messaging"][0]
        except (KeyError, IndexError):
            return None

        message = event.get("message", {})
        text: str = message.get("text", "").strip()
        if not text or message.get("is_echo"):
            return None

        sender_id = str(event.get("sender", {}).get("id", ""))
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
                "mid": message.get("mid"),
                "is_command": text.startswith("/"),
            },
        )

    async def send_message(self, receiver_id: str, message: str, **kwargs) -> None:
        await self._call_graph("messages", {
            "recipient": {"id": receiver_id},
            "message": {"text": message},
            "messaging_type": "RESPONSE",
        })

    async def send_typing(self, receiver_id: str) -> None:
        await self._call_graph("messages", {
            "recipient": {"id": receiver_id},
            "sender_action": "typing_on",
        })

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

    async def _call_graph(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        url = f"{_GRAPH_API}/me/{endpoint}"
        params = {"access_token": settings.MESSENGER_PAGE_ACCESS_TOKEN}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=data, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            custom_logger.error(
                f"[MessengerAdapter] API error | endpoint={endpoint} | "
                f"status={exc.response.status_code} | detail={exc.response.text[:300]}"
            )
            raise
        except httpx.RequestError as exc:
            custom_logger.error(f"[MessengerAdapter] request failed | endpoint={endpoint} | error={exc}")
            raise
