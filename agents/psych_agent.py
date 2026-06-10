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

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from core.config import settings
from graph.state import ConversationState, PsychState
from utils.helper import read_file_contents

_PSYCH_PROMPT = read_file_contents("resources/prompt/psych_agent.md")


def _build_psych_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=settings.ANTHROPIC_MODEL_FAST,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.0,
        max_tokens=256,
    )


def _format_conversation_history(messages: list, max_turns: int = 10) -> str:
    """Format last N turns for the Psych Agent context window."""
    recent = messages[-max_turns * 2:]
    lines: list[str] = []
    for msg in recent:
        role = "Khách hàng" if getattr(msg, "type", "") == "human" else "Tư vấn viên"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines) if lines else "(Chưa có lịch sử)"


def psych_agent_node(state: ConversationState) -> dict:
    """
    LangGraph node function for the Psych Agent.
    Returns a state delta with: psych_state, psych_confidence, primary_concern, consult_strategy.
    """
    llm = _build_psych_llm()

    conversation_text = _format_conversation_history(state.get("messages", []))

    response = llm.invoke([
        SystemMessage(content=_PSYCH_PROMPT),
        HumanMessage(content=f"Lịch sử hội thoại:\n{conversation_text}"),
    ])

    try:
        parsed = json.loads(response.content)
        psych_state_raw = parsed.get("psych_state", "CURIOUS")
        psych_state = PsychState(psych_state_raw) if psych_state_raw in PsychState._value2member_map_ else PsychState.CURIOUS
        psych_confidence = float(parsed.get("psych_confidence", 0.5))
        primary_concern = parsed.get("primary_concern")
        consult_strategy = parsed.get("consult_strategy", "Tiếp tục tư vấn")
    except (json.JSONDecodeError, AttributeError, ValueError):
        psych_state = PsychState.CURIOUS
        psych_confidence = 0.5
        primary_concern = None
        consult_strategy = "Tiếp tục tư vấn chung"

    return {
        "psych_state": psych_state,
        "psych_confidence": psych_confidence,
        "primary_concern": primary_concern,
        "consult_strategy": consult_strategy,
        "next_node": "orchestrator",  # always returns to orchestrator
        "error_state": None,
    }
