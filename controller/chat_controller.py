"""
Chat Controller — Interface Layer logic between REST endpoints and the LangGraph graph.

Responsibilities (thesis §3.1.2 — Interface Layer):
  - Authenticate request and validate session
  - Recover ConversationState from Redis via thread_id
  - Invoke compiled LangGraph graph
  - Persist turn to MySQL (ConversationSessions + ConversationMessages)
  - Return structured ChatResponse with latency metrics
"""

import asyncio
import time
import uuid

from langchain_core.messages import HumanMessage

from core.logger import custom_logger
from graph.graph import get_compiled_graph
from schemas.chat_schema import ChatRequest, ChatResponse


async def handle_chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat handler. Creates or recovers a session, invokes the MAS graph,
    persists the turn to MySQL, and returns the synthesized response.
    """
    session_id = request.session_id or str(uuid.uuid4())
    graph = get_compiled_graph()

    config = {
        "configurable": {
            "thread_id": session_id,
        }
    }

    # Seed the input state with the new user message.
    # LangGraph's add_messages reducer appends this to existing conversation history
    # recovered from the Redis checkpoint for this thread_id.
    input_state = {
        "messages": [HumanMessage(content=request.message)],
        "session_metadata": {
            "session_id": session_id,
            "channel": request.channel,
            "user_id": request.user_id,
            "timestamp": time.time(),
        },
        "iteration_count": 0,
        "retrieved_products": [],
        "retrieval_scores": [],
        "final_response": "",
        "error_state": None,
    }

    t0 = time.perf_counter()
    result = await graph.ainvoke(input_state, config=config)
    latency_ms = (time.perf_counter() - t0) * 1000

    final_response = result.get("final_response", "")
    psych_state = result.get("psych_state")
    consult_strategy = result.get("consult_strategy")
    iteration_count = result.get("iteration_count", 0)

    # Persist turn to MySQL without blocking the response — errors are logged, not raised.
    asyncio.create_task(
        _persist_turn_async(
            session_id=session_id,
            user_id=request.user_id,
            channel=request.channel,
            user_message=request.message,
            assistant_response=final_response,
            psych_state=psych_state.value if psych_state else None,
            consult_strategy=consult_strategy,
            iteration_count=iteration_count,
            latency_ms=round(latency_ms),
        )
    )

    return ChatResponse(
        session_id=session_id,
        response=final_response,
        psych_state=psych_state,
        psych_confidence=result.get("psych_confidence"),
        consult_strategy=consult_strategy,
        retrieved_product_count=len(result.get("retrieved_products", [])),
        latency_ms=round(latency_ms, 2),
        iteration_count=iteration_count,
    )


async def _persist_turn_async(
    session_id: str,
    user_id: int | None,
    channel: str,
    user_message: str,
    assistant_response: str,
    psych_state: str | None,
    consult_strategy: str | None,
    iteration_count: int,
    latency_ms: int,
) -> None:
    """Run synchronous DB writes off the event loop thread."""
    try:
        await asyncio.to_thread(
            _persist_turn,
            session_id,
            user_id,
            channel,
            user_message,
            assistant_response,
            psych_state,
            consult_strategy,
            iteration_count,
            latency_ms,
        )
    except Exception as exc:
        custom_logger.warning(f"DB persist failed for session {session_id}: {exc}")


def _persist_turn(
    session_id: str,
    user_id: int | None,
    channel: str,
    user_message: str,
    assistant_response: str,
    psych_state: str | None,
    consult_strategy: str | None,
    iteration_count: int,
    latency_ms: int,
) -> None:
    from database import get_db
    from repositories.conversation_repository import ConversationRepository

    with get_db() as db:
        repo = ConversationRepository(db)

        session = repo.upsert_session(session_id, user_id, channel)
        turn_number = (session.total_turns or 0) + 1

        repo.log_message(
            session_id=session.id,
            turn_number=turn_number,
            role="user",
            content=user_message,
        )
        repo.log_message(
            session_id=session.id,
            turn_number=turn_number,
            role="assistant",
            content=assistant_response,
            agent_name="synth_agent",
            latency_ms=latency_ms,
        )
        repo.update_session_after_turn(
            session=session,
            psych_state=psych_state,
            consult_strategy=consult_strategy,
            iteration_count=iteration_count,
        )
