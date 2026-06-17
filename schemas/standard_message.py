from typing import Any, Optional

from pydantic import BaseModel


class StandardMessage(BaseModel):
    platform: str
    bot_name: str
    sender_id: str
    session_key: str
    message: str
    raw_payload: dict[str, Any] = {}
    metadata: Optional[dict[str, Any]] = None
