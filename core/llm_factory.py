"""
LLM Factory — chọn provider (Anthropic hoặc Google Gemini/AI Studio) theo settings.LLM_PROVIDER
(xem core/config.py), để từng agent không phải tự biết chi tiết SDK của mỗi provider.

Anthropic hỗ trợ prompt caching qua content-block "cache_control" trên SystemMessage (giảm chi
phí/độ trễ vì system prompt không đổi giữa các lượt). Gemini không có cú pháp tương đương trong
LangChain, nên build_system_message() tự bỏ "cache_control" khi provider là gemini thay vì rải
if/else provider ở từng agent gọi LLM (base_agent.py, orchestrator.py, synth_agent.py).
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage

from core.config import settings


def build_chat_model(model_key: str, *, temperature: float, max_tokens: int) -> BaseChatModel:
    """
    @desc Khởi tạo chat model theo provider đang cấu hình ở settings.LLM_PROVIDER
    @params model_key (str): "PRIMARY" (Orchestrator + Synth Agent) hoặc "FAST" (KR/Psych/Extraction)
    @params temperature (float): Độ ngẫu nhiên sinh văn bản
    @params max_tokens (int): Số token tối đa cho phản hồi
    @return BaseChatModel: Instance LangChain chat model đã cấu hình theo đúng provider
    """
    if settings.LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = settings.GEMINI_MODEL_PRIMARY if model_key == "PRIMARY" else settings.GEMINI_MODEL_FAST
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
            # Gemini 3.x bật "thinking" ngầm mặc định — tiêu tốn 1 phần max_tokens cho suy luận
            # ẩn trước khi sinh câu trả lời thật, dễ khiến response bị cắt cụt với các max_tokens
            # vốn được tính toán cho hành vi "không có token ẩn" (kiểu Anthropic không bật extended
            # thinking). Tắt hẳn để giữ đúng ngân sách token đã tune cho từng agent.
            thinking_budget=0,
        )

    from langchain_anthropic import ChatAnthropic

    model = settings.ANTHROPIC_MODEL_PRIMARY if model_key == "PRIMARY" else settings.ANTHROPIC_MODEL_FAST

    reasoning_kwargs: dict = {}
    if model_key == "PRIMARY":
        # Reasoning model: tier PRIMARY (Orchestrator định tuyến + Synth Agent tổng hợp câu trả
        # lời) bật adaptive thinking — Claude tự quyết định có suy luận và suy luận sâu tới đâu
        # trước khi trả lời, thay cho budget_tokens cố định (đã deprecated trên dòng model 4.x).
        # Tier FAST (KR/Psych/Extraction) không bật để giữ tốc độ phân loại/trích xuất nhanh.
        # Thinking tokens tính chung vào max_tokens của request — nới sàn tối thiểu để model có
        # đủ chỗ suy luận mà không bị cắt cụt phần trả lời thật sự (response.text vẫn chỉ lấy
        # block "text", thinking block bị bỏ qua nên không ảnh hưởng parse JSON/streaming hiện có).
        reasoning_kwargs["thinking"] = {"type": "adaptive"}
        reasoning_kwargs["effort"] = settings.ANTHROPIC_REASONING_EFFORT
        max_tokens = max(max_tokens, settings.ANTHROPIC_REASONING_MIN_MAX_TOKENS)

        # Anthropic API từ chối request với 400 invalid_request_error nếu temperature != 1 khi
        # thinking đang bật/adaptive ("temperature may only be set to 1 when thinking is enabled
        # or in adaptive mode"). Bỏ hẳn tham số thay vì set cứng =1 — None bị loại khỏi request
        # payload (xem ChatAnthropic._get_request_payload), để Anthropic tự áp default, tránh
        # hard-code một con số có thể lệch với default thực tế của API sau này.
        temperature = None

    return ChatAnthropic(
        model=model,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
        **reasoning_kwargs,
    )


def build_system_message(text: str) -> SystemMessage:
    """
    @desc Tạo SystemMessage phù hợp với provider đang cấu hình — bật prompt caching kiểu Anthropic
    khi provider là "anthropic", trả về SystemMessage văn bản thuần khi provider là "gemini"
    @params text (str): Nội dung system prompt
    @return SystemMessage: Message đã định dạng đúng theo provider
    """
    if settings.LLM_PROVIDER == "gemini":
        return SystemMessage(content=text)
    return SystemMessage(content=[{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}])
