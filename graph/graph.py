"""
LangGraph StateGraph assembly — wires all agents into the DCG (Directed Cyclic Graph).

Graph topology (thesis §3.3.2 + Figure):
  START → orchestrator
  orchestrator →[conditional: next_node]→ kr_agent | psych_agent | synth_agent | error_handler | END
  kr_agent     →[normal]→ orchestrator   (sole control always returns here)
  psych_agent  →[normal]→ orchestrator   (sole control always returns here)
  synth_agent  →[normal]→ END            (response generated, turn complete)
  error_handler→[normal]→ END

Checkpointing: Redis checkpointer stores state per thread_id:checkpoint_id with TTL=3600s.
"""

from langchain_core.messages import AIMessage
from langgraph.checkpoint.redis import RedisSaver
from langgraph.graph import END, START, StateGraph

from agents.kr_agent import kr_agent_node
from agents.orchestrator import orchestrator_node
from agents.psych_agent import psych_agent_node
from agents.synth_agent import synth_agent_node
from core.config import settings
from graph.router import conditional_router
from graph.state import ConversationState


def _error_handler_node(state: ConversationState) -> dict:
    """Graceful degradation — returns a fallback response when any agent fails."""
    error_msg = state.get("error_state", "Đã xảy ra lỗi không xác định")
    return {
        "final_response": (
            "Xin lỗi, hệ thống đang gặp sự cố tạm thời. "
            "Bạn vui lòng thử lại sau ít phút hoặc liên hệ trực tiếp với nhân viên tư vấn. "
            f"[Debug: {error_msg}]"
        ),
        "error_state": None,
    }


def _build_graph() -> StateGraph:
    graph = StateGraph(ConversationState)

    # Register nodes
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("kr_agent", kr_agent_node)
    graph.add_node("psych_agent", psych_agent_node)
    graph.add_node("synth_agent", synth_agent_node)
    graph.add_node("error_handler", _error_handler_node)

    # Entry point
    graph.add_edge(START, "orchestrator")

    # Conditional edges from Orchestrator — reads state["next_node"]
    graph.add_conditional_edges(
        "orchestrator",
        conditional_router,
        {
            "kr_agent": "kr_agent",
            "psych_agent": "psych_agent",
            "synth_agent": "synth_agent",
            "error_handler": "error_handler",
            END: END,
        },
    )

    # Normal edges — KR and Psych always return control to Orchestrator
    graph.add_edge("kr_agent", "orchestrator")
    graph.add_edge("psych_agent", "orchestrator")

    # Synth Agent completes the turn
    graph.add_edge("synth_agent", END)
    graph.add_edge("error_handler", END)

    return graph


def _build_redis_checkpointer() -> RedisSaver:
    redis_url = (
        f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
        if settings.REDIS_PASSWORD
        else f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
    )
    return RedisSaver.from_conn_string(redis_url)


def compile_graph():
    """
    Compile and return the LangGraph application with Redis checkpointing.
    Call once at startup and reuse across requests.
    """
    checkpointer = _build_redis_checkpointer()
    graph = _build_graph()
    return graph.compile(checkpointer=checkpointer)


# Module-level compiled graph — initialized lazily on first use
_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = compile_graph()
    return _compiled_graph
