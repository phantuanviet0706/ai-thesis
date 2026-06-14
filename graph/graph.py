"""
LangGraph StateGraph assembly — wires all agents into the DCG (Directed Cyclic Graph).

Graph topology (thesis §3.3.2 + Figure):
  START → orchestrator
  orchestrator →[conditional: next_node]→ kr_agent | psych_agent | synth_agent | error_handler | END
  kr_agent     →[normal]→ orchestrator   (sole control always returns here)
  psych_agent  →[normal]→ orchestrator   (sole control always returns here)
  synth_agent  →[normal]→ END            (response generated, turn complete)
  error_handler→[normal]→ END

Checkpointing: Redis Stack checkpointer (preferred) or AsyncSQLite fallback (persistent).
"""

import os

from langchain_core.messages import AIMessage  # used in _error_handler_node
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis import RedisSaver
from langgraph.graph import END, START, StateGraph

try:
    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    _SQLITE_AVAILABLE = True
except ImportError:
    AsyncSqliteSaver = None
    _SQLITE_AVAILABLE = False

from agents.kr_agent import kr_agent_node
from agents.orchestrator import orchestrator_node
from agents.psych_agent import psych_agent_node
from agents.synth_agent import synth_agent_node
from core.logger import custom_logger
from graph.router import conditional_router
from graph.state import ConversationState
from infrastructure.redis_client import redis_client


def _error_handler_node(state: ConversationState) -> dict:
    """
    @desc Node xử lý lỗi — trả về phản hồi dự phòng thân thiện khi bất kỳ agent nào gặp sự cố
    @params state (ConversationState): Trạng thái hội thoại chứa thông tin lỗi trong trường error_state
    @return dict: State delta gồm messages (AIMessage dự phòng), final_response và error_state được xóa về None
    """
    error_msg = state.get("error_state", "Đã xảy ra lỗi không xác định")
    custom_logger.error(f"[Graph] error_handler triggered | error='{error_msg}'")
    fallback = (
        "Xin lỗi, hệ thống đang gặp sự cố tạm thời. "
        "Bạn vui lòng thử lại sau ít phút hoặc liên hệ trực tiếp với nhân viên tư vấn. "
        f"[Debug: {error_msg}]"
    )
    return {
        "messages": [AIMessage(content=fallback)],
        "final_response": fallback,
        "error_state": None,
    }


def _build_graph() -> StateGraph:
    """
    @desc Xây dựng cấu trúc StateGraph với 5 node và các cạnh kết nối theo kiến trúc DCG của luận văn
    @return StateGraph: Đồ thị trạng thái chưa được biên dịch gồm orchestrator, kr_agent, psych_agent, synth_agent và error_handler
    """
    graph = StateGraph(ConversationState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("kr_agent", kr_agent_node)
    graph.add_node("psych_agent", psych_agent_node)
    graph.add_node("synth_agent", synth_agent_node)
    graph.add_node("error_handler", _error_handler_node)

    graph.add_edge(START, "orchestrator")

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

    graph.add_edge("kr_agent", "orchestrator")
    graph.add_edge("psych_agent", "orchestrator")
    graph.add_edge("synth_agent", END)
    graph.add_edge("error_handler", END)

    return graph


def _is_redis_stack_available() -> bool:
    """Probe Redis Stack availability silently — no logs, no exceptions."""
    try:
        redis_client.execute_command("FT._LIST")
        return True
    except Exception:
        return False


async def _build_sqlite_checkpointer():
    """AsyncSQLite persistent checkpointer — requires langgraph-checkpoint-sqlite."""
    if not _SQLITE_AVAILABLE:
        raise ImportError("pip install langgraph-checkpoint-sqlite")
    db_dir = "data"
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "checkpoints.db")
    conn = await aiosqlite.connect(db_path)
    saver = AsyncSqliteSaver(conn)
    await saver.setup()
    custom_logger.info(f"[Graph] AsyncSQLite checkpointer ready at '{db_path}'")
    return saver


async def _build_checkpointer():
    """
    @desc Khởi tạo checkpointer theo thứ tự ưu tiên:
    1. Redis Stack (nếu có RediSearch module) — production
    2. AsyncSQLite (persistent, không cần Redis Stack) — dev/thesis
    3. MemorySaver (in-memory, last resort) — state mất khi restart
    """
    custom_logger.info("[Graph] Setting up checkpointer...")

    if _is_redis_stack_available():
        try:
            saver = RedisSaver(redis_client=redis_client)
            saver.setup()
            custom_logger.info("[Graph] Redis Stack checkpointer ready")
            return saver
        except Exception as exc:
            custom_logger.warning(f"[Graph] Redis Stack setup failed unexpectedly: {exc}")

    custom_logger.info("[Graph] Redis Stack not detected — using AsyncSQLite checkpointer (persistent)")

    try:
        return await _build_sqlite_checkpointer()
    except Exception as exc:
        custom_logger.warning(f"[Graph] SQLite unavailable ({exc}) — using MemorySaver (not persistent)")
        return MemorySaver()


async def compile_graph():
    """
    @desc Biên dịch và trả về ứng dụng LangGraph hoàn chỉnh với checkpointing, nên gọi một lần khi khởi động
    @return CompiledGraph: Đồ thị đã được biên dịch với checkpointer, sẵn sàng xử lý yêu cầu
    """
    custom_logger.info("[Graph] Compiling LangGraph application (5 nodes)...")
    try:
        checkpointer = await _build_checkpointer()
        graph = _build_graph()
        compiled = graph.compile(checkpointer=checkpointer)
        custom_logger.info("[Graph] Compilation complete — checkpointing enabled")
        return compiled
    except Exception as exc:
        custom_logger.error(f"[Graph] Compilation failed: {exc}", exc_info=True)
        raise


_compiled_graph = None


async def get_compiled_graph():
    """
    @desc Trả về instance đồ thị đã biên dịch theo pattern Singleton, tự động biên dịch lần đầu nếu chưa có
    @return CompiledGraph: Instance đồ thị LangGraph dùng chung cho toàn bộ ứng dụng
    """
    global _compiled_graph
    if _compiled_graph is None:
        custom_logger.info("[Graph] Lazy compile triggered")
        _compiled_graph = await compile_graph()
    return _compiled_graph
