"""
Orchestrator Agent — cognitive center and sole routing authority of the MAS.

Responsibilities (thesis §3.2.1):
  1. Intent Analysis: identify high-level user intent from messages + state
  2. State Evaluation: assess what information is available vs. still needed
  3. Routing Decision: select next specialized agent via CoT reasoning

Uses structured JSON output (not free-text) to minimize routing errors.
Action space A = {kr_agent, psych_agent, synth_agent.md, END}
"""

import json
import time
from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from constants.constants import ORCHESTRATOR_FORCE_SYNTH_ITERATION, PSYCH_CONFIDENCE_THRESHOLD
from core.config import settings
from core.logger import custom_logger
from graph.state import ConversationState
from utils.helper import extract_json, read_file_contents

_SYSTEM_PROMPT = read_file_contents("resources/prompt/orchestrator_agent.md")


@lru_cache(maxsize=1)
def _get_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=settings.ANTHROPIC_MODEL_PRIMARY,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.0,
        max_tokens=600,
    )


def orchestrator_node(state: ConversationState) -> dict:
    """
    @desc Node LangGraph của Orchestrator Agent — phân tích ý định người dùng và quyết định agent tiếp theo
    @params state (ConversationState): Trạng thái hội thoại chứa lịch sử tin nhắn và kết quả từ các agent
    @return dict: State delta gồm next_node, user_intent và iteration_count tăng thêm 1
    """
    t0 = time.perf_counter()
    iteration = state.get("iteration_count", 0)
    custom_logger.info(f"[Orchestrator] start | iter={iteration}")

    # Upstream agent failed — stop immediately, do not call LLM
    if state.get("error_state"):
        custom_logger.warning(
            f"[Orchestrator] upstream error detected → error_handler | "
            f"error='{state['error_state']}' | iter={iteration}"
        )
        return {"next_node": "error_handler", "iteration_count": iteration + 1}

    has_products = bool(state.get("retrieved_products"))
    has_response = bool(state.get("final_response"))

    # KR Agent already ran with no results — skip LLM, go directly to synth for fallback response
    if not has_products and iteration > 0:
        custom_logger.info(
            f"[Orchestrator] no products after KR run → synth_agent (fallback) | iter={iteration}"
        )
        return {
            "next_node": "synth_agent",
            "user_intent": state.get("user_intent", ""),
            "iteration_count": iteration + 1,
            "error_state": None,
        }

    # Từ vòng lặp thứ 2 trong CÙNG một lượt chat trở đi (iteration > 0), ý định đã được
    # LLM phân loại ở vòng đầu (iteration=0) — không có đường nào trong graph khiến
    # orchestrator phải phân loại lại ý định giữa chừng (kr_agent/psych_agent chỉ bổ
    # sung dữ liệu, không đổi topic của lượt hiện tại). Quyết định kế tiếp lúc này hoàn
    # toàn xác định được từ state theo đúng 2 nhánh cuối của bảng định tuyến trong
    # orchestrator_agent.md — bỏ qua lệnh gọi LLM (Sonnet) để giảm latency mỗi lượt.
    if iteration > 0 and not has_response:
        psych_confidence = state.get("psych_confidence") or 0.0
        needs_psych = state.get("psych_state") is None or psych_confidence < PSYCH_CONFIDENCE_THRESHOLD
        next_node = (
            "psych_agent" if needs_psych and iteration < ORCHESTRATOR_FORCE_SYNTH_ITERATION
            else "synth_agent"
        )
        custom_logger.info(
            f"[Orchestrator] rule-based (skip LLM) → {next_node} | "
            f"psych_confidence={psych_confidence:.2f} | iter={iteration}"
        )
        return {
            "next_node": next_node,
            "user_intent": state.get("user_intent", ""),
            "iteration_count": iteration + 1,
            "error_state": None,
        }

    state_summary = (
        f"retrieved_products: {'có (' + str(len(state['retrieved_products'])) + ' sản phẩm)' if has_products else 'chưa có'}\n"
        f"psych_state: {state.get('psych_state', 'chưa phân tích')} "
        f"(confidence={state.get('psych_confidence', 0):.2f})\n"
        f"final_response: {'đã có' if has_response else 'chưa có'}\n"
        f"iteration_count: {iteration}"
    )

    messages = state.get("messages", [])
    last_user_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break

    user_prompt = (
        f"Tin nhắn mới nhất của khách hàng:\n{last_user_message}\n\n"
        f"Trạng thái hiện tại:\n{state_summary}"
    )

    response = _get_llm().invoke([
        SystemMessage(content=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]),
        HumanMessage(content=user_prompt),
    ])

    next_node = "END"
    user_intent = ""
    try:
        parsed = extract_json(response.content)
        next_node = parsed.get("next_node", "END")
        user_intent = parsed.get("user_intent", "")
    except (json.JSONDecodeError, AttributeError, ValueError):
        latency = (time.perf_counter() - t0) * 1000
        raw = getattr(response, "content", str(response))
        error_msg = f"Orchestrator LLM trả về định dạng không hợp lệ | iter={iteration}"
        custom_logger.warning(
            f"[Orchestrator] JSON parse failed → error_handler | {latency:.0f}ms | iter={iteration} "
            f"| raw_response='{raw[:300]}'"
        )
        return {
            "next_node": "error_handler",
            "user_intent": "",
            "iteration_count": iteration + 1,
            "error_state": error_msg,
        }

    latency = (time.perf_counter() - t0) * 1000
    custom_logger.info(
        f"[Orchestrator] complete | next={next_node} | "
        f"intent='{user_intent[:60]}' | {latency:.0f}ms | iter={iteration}"
    )

    return {
        "next_node": next_node,
        "user_intent": user_intent,
        "iteration_count": iteration + 1,
        "error_state": None,
    }
