"""
Psychology Analysis Agent (Psych Agent) — novel architectural contribution.

Treats customer psychological state inference as a first-class autonomous agent,
not a passive post-hoc tool. Continuously shapes the system's consultation strategy.

Classification approach (thesis §3.2.3):
  Zero-shot LLM classification — no annotated data required (critical for Vietnamese context).
  Achieved F1=0.78 on purchase intent classification (Hou et al. 2023).

Multi-dimensional linguistic features analysed:
  - Lexical: hesitation ("suy nghĩ", "có lẽ"), comparative ("hay là"), commitment ("đặt ngay")
  - Syntactic: confirmation questions, negative sentences
  - Sentiment: polarity + intensity
  - Contextual: elapsed turns, query complexity

Output governs how Synth Agent frames the final response (feedback loop).
"""

import json
import time

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from core.config import settings
from core.logger import custom_logger
from graph.state import ConversationState, PsychState
from utils.helper import read_file_contents

_PSYCH_PROMPT = read_file_contents("resources/prompt/psych_agent.md")


def _build_psych_llm() -> ChatAnthropic:
    """
    @desc Khởi tạo LLM tốc độ cao (Haiku) dùng cho Psych Agent
    @return ChatAnthropic: Instance ChatAnthropic với temperature=0 và max_tokens=256
    """
    return ChatAnthropic(
        model=settings.ANTHROPIC_MODEL_FAST,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.0,
        max_tokens=256,
    )


def _format_conversation_history(messages: list, max_turns: int = 10) -> str:
    """
    @desc Định dạng N lượt hội thoại gần nhất thành chuỗi văn bản cho context window của Psych Agent
    @params messages (list): Danh sách các tin nhắn trong lịch sử hội thoại
    @params max_turns (int): Số lượt hội thoại tối đa cần lấy, mặc định là 10
    @return str: Chuỗi văn bản lịch sử hội thoại đã được định dạng theo vai trò người dùng và tư vấn viên
    """
    recent = messages[-max_turns * 2:]
    lines: list[str] = []
    for msg in recent:
        role = "Khách hàng" if getattr(msg, "type", "") == "human" else "Tư vấn viên"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines) if lines else "(Chưa có lịch sử)"


def psych_agent_node(state: ConversationState) -> dict:
    """
    @desc Node LangGraph của Psych Agent — phân tích trạng thái tâm lý khách hàng từ lịch sử hội thoại
    @params state (ConversationState): Trạng thái hội thoại chứa lịch sử tin nhắn và metadata session
    @return dict: State delta gồm psych_state, psych_confidence, primary_concern và consult_strategy
    """
    t0 = time.perf_counter()
    msg_count = len(state.get("messages", []))
    custom_logger.info(f"[Psych Agent] start | history_msgs={msg_count}")

    llm = _build_psych_llm()
    conversation_text = _format_conversation_history(state.get("messages", []))

    response = llm.invoke([
        SystemMessage(content=_PSYCH_PROMPT),
        HumanMessage(content=f"Lịch sử hội thoại:\n{conversation_text}"),
    ])

    psych_state = PsychState.CURIOUS
    psych_confidence = 0.5
    primary_concern = None
    consult_strategy = "Tiếp tục tư vấn chung"

    try:
        parsed = json.loads(response.content)
        psych_state_raw = parsed.get("psych_state", "CURIOUS")
        psych_state = PsychState(psych_state_raw) if psych_state_raw in PsychState._value2member_map_ else PsychState.CURIOUS
        psych_confidence = float(parsed.get("psych_confidence", 0.5))
        primary_concern = parsed.get("primary_concern")
        consult_strategy = parsed.get("consult_strategy", "Tiếp tục tư vấn")

        custom_logger.info(
            f"[Psych Agent] classified | state={psych_state.value} | "
            f"confidence={psych_confidence:.2f} | concern='{primary_concern}' | "
            f"strategy='{consult_strategy[:50]}'"
        )
    except (json.JSONDecodeError, AttributeError, ValueError):
        custom_logger.warning("[Psych Agent] JSON parse failed, using default CURIOUS state")

    latency = (time.perf_counter() - t0) * 1000
    custom_logger.info(f"[Psych Agent] complete | {latency:.0f}ms")

    return {
        "psych_state": psych_state,
        "psych_confidence": psych_confidence,
        "primary_concern": primary_concern,
        "consult_strategy": consult_strategy,
        "next_node": "orchestrator",
        "error_state": None,
    }
