"""
BaseLLMAgent — Template Method dùng chung cho các agent có hình dạng:
  build prompt → invoke LLM 1 lần (đồng bộ) → parse JSON output → map vào state delta.

Áp dụng cho: KRAgent, PsychAgent, ExtractionAgent (agents/kr_agent.py, psych_agent.py,
extraction_agent.py). KHÔNG áp dụng cho SynthAgent — synth dùng streaming bất đồng bộ
(.astream()), output là văn bản thô (không phải JSON), và không có bước parse — hình
dạng khác hẳn nên giữ nguyên là function độc lập thay vì ép vào cùng 1 khuôn.

Cùng công thức Template Method + Registry đã dùng ở adapter/ (BaseAdapter +
AdapterRegistry): agent con chỉ implement 2 hook (build_user_prompt, parse_response),
__call__() lo phần còn lại (gọi LLM với cache_control, đo latency, log, bắt lỗi).
"""

import time
from abc import ABC, abstractmethod

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from core.config import settings
from core.logger import custom_logger
from graph.state import ConversationState
from utils.helper import read_file_contents


class BaseLLMAgent(ABC):
    prompt_path: str
    log_tag: str
    model_key: str = "FAST"  # "FAST" -> ANTHROPIC_MODEL_FAST | "PRIMARY" -> ANTHROPIC_MODEL_PRIMARY
    temperature: float = 0.0
    max_tokens: int = 400

    def __init__(self) -> None:
        self._system_prompt = read_file_contents(self.prompt_path)
        # Instance được tạo 1 lần duy nhất khi graph compile (xem graph/graph.py) và tái sử
        # dụng suốt vòng đời app — lazy-init này tương đương @lru_cache(maxsize=1) cũ, chỉ
        # tạo 1 ChatAnthropic client và dùng lại cho mọi request sau đó.
        self._llm: ChatAnthropic | None = None

    def _get_llm(self) -> ChatAnthropic:
        if self._llm is None:
            model = (
                settings.ANTHROPIC_MODEL_PRIMARY if self.model_key == "PRIMARY"
                else settings.ANTHROPIC_MODEL_FAST
            )
            self._llm = ChatAnthropic(
                model=model,
                api_key=settings.ANTHROPIC_API_KEY,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        return self._llm

    @abstractmethod
    def build_user_prompt(self, state: ConversationState) -> str:
        """Xây dựng nội dung HumanMessage từ state — mỗi agent tự override."""

    @abstractmethod
    def parse_response(self, raw_content: str, state: ConversationState) -> dict:
        """
        Parse output LLM (JSON) thành state delta — mỗi agent tự override.
        Có thể làm thêm side-effect cần thiết trước khi trả về (vd KRAgent gọi
        hybrid_search sau khi có enriched_query từ JSON).
        """

    def on_error(self, exc: Exception, state: ConversationState) -> dict:
        """
        Fallback khi invoke LLM hoặc parse_response lỗi (bắt Exception rộng — khớp với
        phạm vi bắt lỗi rộng nhất trong 3 agent gốc). Override nếu agent cần fallback
        riêng thay vì set error_state (vd Psych Agent trả về CURIOUS mặc định).
        """
        custom_logger.error(f"[{self.log_tag}] error: {exc}", exc_info=True)
        return {"error_state": f"{self.log_tag} error: {exc}"}

    def __call__(self, state: ConversationState) -> dict:
        t0 = time.perf_counter()
        custom_logger.info(f"[{self.log_tag}] start")
        try:
            user_prompt = self.build_user_prompt(state)
            response = self._get_llm().invoke([
                SystemMessage(content=[{
                    "type": "text",
                    "text": self._system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }]),
                HumanMessage(content=user_prompt),
            ])
            delta = self.parse_response(response.content, state)
        except Exception as exc:
            delta = self.on_error(exc, state)

        latency = (time.perf_counter() - t0) * 1000
        custom_logger.info(f"[{self.log_tag}] complete | {latency:.0f}ms")
        return delta
