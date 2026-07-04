from typing import Optional
from pydantic import Field

from graph.state import PsychState
from schemas.base_schema import BaseSchema


class ChatRequest(BaseSchema):
    session_id: Optional[str] = Field(
        default=None,
        description="UUID v4 thread_id for session continuity. Omit to start a new session."
    )
    message: str = Field(..., min_length=1, max_length=2000)
    channel: str = Field(default="web", description="web | mobile | facebook | zalo | tiktok")
    user_id: Optional[int] = Field(default=None, description="Authenticated user ID if available")


class ChatResponse(BaseSchema):
    session_id: str
    response: str
    psych_state: Optional[PsychState] = None
    psych_confidence: Optional[float] = None
    consult_strategy: Optional[str] = None
    retrieved_product_count: int = 0
    latency_ms: float
    iteration_count: int = 0
