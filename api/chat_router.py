"""
Chat API Router — Interface Layer endpoints (thesis §3.4.4).

Endpoints:
  POST /v1/chat          — synchronous response (30s timeout)
  GET  /v1/chat/stream   — Server-Sent Events for token-by-token streaming

Rate limiting: 100 requests/minute/session via Redis Token Bucket (enforced in middleware).
CORS: restricted to approved retail partner domains (configured in main.py).
"""

import asyncio
import json
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from controller.chat_controller import handle_chat
from schemas.api_schema import ApiResponse
from schemas.chat_schema import ChatRequest, ChatResponse

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


@chat_router.post("", response_model=ApiResponse[ChatResponse])
async def chat(request: ChatRequest):
    """Synchronous chat endpoint with 30-second timeout."""
    try:
        response = await asyncio.wait_for(handle_chat(request), timeout=30.0)
        return ApiResponse(code=200, message="Success", result=response)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timeout — MAS exceeded 30s")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@chat_router.get("/stream")
async def chat_stream(
    message: str,
    session_id: str | None = None,
    channel: str = "web",
):
    """
    Server-Sent Events streaming endpoint.
    Streams the final_response token-by-token after graph completion.
    """
    request = ChatRequest(
        session_id=session_id,
        message=message,
        channel=channel,
    )

    async def event_generator():
        try:
            response = await handle_chat(request)
            # Stream the response word-by-word (token simulation)
            words = response.response.split()
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                data = json.dumps({"token": chunk, "done": False})
                yield f"data: {data}\n\n"
                await asyncio.sleep(0.01)

            # Final event with full metadata
            meta = json.dumps({
                "done": True,
                "session_id": response.session_id,
                "psych_state": response.psych_state,
                "latency_ms": response.latency_ms,
            })
            yield f"data: {meta}\n\n"

        except Exception as exc:
            error_data = json.dumps({"error": str(exc), "done": True})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
