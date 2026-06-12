from langgraph.graph import END

from constants.constants import MAX_ITERATIONS, VALID_NODES
from core.logger import custom_logger
from graph.state import ConversationState


def conditional_router(state: ConversationState) -> str:
    """
    @desc Đọc trạng thái sau mỗi lần Orchestrator chạy để quyết định node tiếp theo, có bảo vệ chống lỗi và vòng lặp vô hạn
    @params state (ConversationState): Trạng thái hội thoại hiện tại chứa next_node, error_state và iteration_count
    @return str: Tên node tiếp theo cần điều hướng tới, hoặc END nếu vượt giới hạn lặp hoặc có lỗi
    """
    iteration = state.get("iteration_count", 0)

    if state.get("error_state") is not None:
        custom_logger.warning(
            f"[Router] error_state detected → error_handler | iter={iteration} | "
            f"error='{state['error_state']}'"
        )
        return "error_handler"

    if iteration > MAX_ITERATIONS:
        custom_logger.warning(
            f"[Router] MAX_ITERATIONS={MAX_ITERATIONS} exceeded → END | iter={iteration}"
        )
        return END

    route = state.get("next_node", "")
    if route not in VALID_NODES:
        custom_logger.warning(
            f"[Router] invalid next_node='{route}' → END | iter={iteration}"
        )
        return END

    custom_logger.info(f"[Router] → {route} | iter={iteration}")
    return route
