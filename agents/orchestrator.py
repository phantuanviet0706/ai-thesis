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
        max_tokens=350,
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
        return {"next_node": "error_handler", "iteration_count": 1}

    has_products = bool(state.get("retrieved_products"))
    has_response = bool(state.get("final_response"))

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
        SystemMessage(content=_SYSTEM_PROMPT),
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
        error_msg = f"Orchestrator LLM trả về định dạng không hợp lệ | iter={iteration}"
        custom_logger.warning(f"[Orchestrator] JSON parse failed → error_handler | {latency:.0f}ms | iter={iteration}")
        return {
            "next_node": "error_handler",
            "user_intent": "",
            "iteration_count": 1,
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
        "iteration_count": 1,
        "error_state": None,
    }
