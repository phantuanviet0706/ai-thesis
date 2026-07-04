from langgraph.graph import END

from constants.constants import MAX_ITERATIONS, PSYCH_CONFIDENCE_THRESHOLD, VALID_NODES
from core.logger import custom_logger
from graph.state import ConversationState


def conditional_router(state: ConversationState) -> str | list[str]:
    """
    @desc Đọc trạng thái sau mỗi lần Orchestrator chạy để quyết định node tiếp theo, có bảo vệ chống lỗi và vòng lặp vô hạn
    @params state (ConversationState): Trạng thái hội thoại hiện tại chứa next_node, error_state và iteration_count
    @return str | list[str]: Tên node tiếp theo, hoặc danh sách node chạy song song (synth_agent + extraction_agent),
        hoặc END nếu vượt giới hạn lặp hoặc có lỗi
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

    if route == "synth_agent":
        # Chạy song song với extraction_agent — extraction chỉ đọc lịch sử hội thoại
        # tới lượt của khách (không cần response của Synth), nên không cần chờ tuần tự.
        # Giúp bỏ hẳn 1 lượt gọi LLM (Haiku) khỏi latency trả lời user.
        custom_logger.info(f"[Router] → synth_agent + extraction_agent (parallel) | iter={iteration}")
        return ["synth_agent", "extraction_agent"]

    if route in ("kr_agent", "psych_agent"):
        # kr_agent và psych_agent không phụ thuộc lẫn nhau (kr_agent chỉ đọc messages;
        # psych_agent chỉ đọc messages — đã verify trong source, không đọc retrieved_products
        # hay psych_state của nhau) — nếu CẢ HAI đều còn thiếu, chạy song song thay vì để
        # Orchestrator quyết định "route" nào trước rồi vòng lại quyết định cái còn lại sau.
        needs_kr = not bool(state.get("retrieved_products"))
        psych_confidence = state.get("psych_confidence") or 0.0
        needs_psych = state.get("psych_state") is None or psych_confidence < PSYCH_CONFIDENCE_THRESHOLD

        if needs_kr and needs_psych:
            custom_logger.info(
                f"[Router] → kr_agent + psych_agent (parallel) | orchestrator_route={route} | "
                f"psych_confidence={psych_confidence:.2f} | iter={iteration}"
            )
            return ["kr_agent", "psych_agent"]

        custom_logger.info(
            f"[Router] → {route} (single — needs_kr={needs_kr} | needs_psych={needs_psych}) | iter={iteration}"
        )
        return route

    custom_logger.info(f"[Router] → {route} | iter={iteration}")
    return route
