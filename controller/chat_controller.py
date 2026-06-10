"""
Chat Controller — Interface Layer logic between REST endpoints and the LangGraph graph.

Responsibilities (thesis §3.1.2 — Interface Layer):
  - Authenticate request and validate session
  - Recover ConversationState from Redis via thread_id
  - Invoke compiled LangGraph graph
  - Return structured ChatResponse with latency metrics
"""

import time
import uuid

from langchain_core.messages import HumanMessage

from graph.graph import get_compiled_graph
from schemas.chat_schema import ChatRequest, ChatResponse


async def handle_chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat handler. Creates or recovers a session, invokes the MAS graph,
    and returns the synthesized response with telemetry fields.
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

    return ChatResponse(
        session_id=session_id,
        response=result.get("final_response", ""),
        psych_state=result.get("psych_state"),
        psych_confidence=result.get("psych_confidence"),
        consult_strategy=result.get("consult_strategy"),
        retrieved_product_count=len(result.get("retrieved_products", [])),
        latency_ms=round(latency_ms, 2),
        iteration_count=result.get("iteration_count", 0),
    )
