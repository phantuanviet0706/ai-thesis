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

from agents.base_agent import BaseLLMAgent
from core.logger import custom_logger
from graph.state import ConversationState, PsychState
from utils.helper import extract_json


def _format_conversation_history(messages: list, max_turns: int = 3) -> str:
    """
    @desc Định dạng N lượt hội thoại gần nhất thành chuỗi văn bản cho context window của Psych Agent
    @params messages (list): Danh sách các tin nhắn trong lịch sử hội thoại
    @params max_turns (int): Số lượt hội thoại tối đa cần lấy, mặc định là 3
    @return str: Chuỗi văn bản lịch sử hội thoại đã được định dạng theo vai trò người dùng và tư vấn viên
    """
    recent = messages[-max_turns * 2:]
    lines: list[str] = []
    for msg in recent:
        role = "Khách hàng" if getattr(msg, "type", "") == "human" else "Tư vấn viên"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines) if lines else "(Chưa có lịch sử)"


class PsychAgent(BaseLLMAgent):
    prompt_path = "resources/prompt/psych_agent.md"
    log_tag = "Psych Agent"
    model_key = "FAST"
    max_tokens = 500

    def build_user_prompt(self, state: ConversationState) -> str:
        conversation_text = _format_conversation_history(state.get("messages", []))
        return f"Lịch sử hội thoại:\n{conversation_text}"

    def parse_response(self, raw_content: str, state: ConversationState) -> dict:
        parsed = extract_json(raw_content)
        psych_state_raw = parsed.get("psych_state", "CURIOUS")
        psych_state = (
            PsychState(psych_state_raw) if psych_state_raw in PsychState._value2member_map_
            else PsychState.CURIOUS
        )
        psych_confidence = float(parsed.get("psych_confidence", 0.65))
        primary_concern = parsed.get("primary_concern")
        consult_strategy = parsed.get("consult_strategy", "Tiếp tục tư vấn")

        custom_logger.info(
            f"[Psych Agent] classified | state={psych_state.value} | "
            f"confidence={psych_confidence:.2f} | concern='{primary_concern}' | "
            f"strategy='{consult_strategy[:50]}'"
        )
        return {
            "psych_state": psych_state,
            "psych_confidence": psych_confidence,
            "primary_concern": primary_concern,
            "consult_strategy": consult_strategy,
        }

    def on_error(self, exc: Exception, state: ConversationState) -> dict:
        # Không set error_state — Psych Agent tự phục hồi bằng fallback CURIOUS thay vì
        # kích hoạt error_handler (giữ đúng hành vi gốc: JSON parse fail không phải lỗi
        # nghiêm trọng, chỉ cần trạng thái tâm lý mặc định để hội thoại tiếp tục trôi chảy).
        custom_logger.warning(f"[Psych Agent] failed, dùng fallback CURIOUS: {exc}")
        return {
            "psych_state": PsychState.CURIOUS,
            "psych_confidence": 0.65,  # above 0.6 threshold — tránh Orchestrator loop lại
            "primary_concern": None,
            "consult_strategy": "Tiếp tục tư vấn chung",
        }


psych_agent_node = PsychAgent()
