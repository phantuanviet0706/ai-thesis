"""
Synthesis Agent (Synth Agent) — final convergence point of the pipeline.

Immutable constraints (thesis §3.2.4):
  1. Factual Grounding: all product info from KR Agent only — zero hallucination tolerance
  2. Strategy Alignment: response structure conforms to Psych Agent's consult_strategy
  3. Natural Tone: friendly, culturally localized Vietnamese register

Response structure follows AIDA marketing model:
  Attention → Interest → Desire → Action (CTA calibrated to psych_state)
"""

import time
from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from core.config import settings
from core.logger import custom_logger
from entity.product_doc import ProductDoc
from graph.state import ConversationState, PsychState
from utils.helper import read_file_contents

_SYNTH_SYSTEM = read_file_contents("resources/prompt/synth_agent.md")


def _format_products_for_synth(products: list[ProductDoc], scores: list[float]) -> str:
    """
    @desc Định dạng danh sách sản phẩm và điểm số thành chuỗi văn bản để đưa vào context của Synth Agent
    @params products (list[ProductDoc]): Danh sách sản phẩm được trả về từ KR Agent (tối đa 3 sản phẩm đầu)
    @params scores (list[float]): Danh sách điểm composite tương ứng với từng sản phẩm
    @return str: Chuỗi văn bản mô tả sản phẩm đã được định dạng, hoặc thông báo không tìm thấy sản phẩm
    """
    if not products:
        return "Không có sản phẩm nào được tìm thấy."

    lines = ["=== SẢN PHẨM TÌM ĐƯỢC ==="]
    for i, (p, score) in enumerate(zip(products[:3], scores[:3]), 1):
        price = f"{p.unit_price:,.0f}₫"
        if p.sale_price and p.sale_price < p.unit_price:
            price = f"~~{p.unit_price:,.0f}₫~~ → {p.sale_price:,.0f}₫"

        chunk_preview = p.chunk_text[:120] + "..." if len(p.chunk_text) > 120 else p.chunk_text

        lines.append(
            f"\n[{i}] {p.name}"
            + (f" (SKU: {p.sku})" if p.sku else "")
            + f"\n    Danh mục: {p.category or 'N/A'} | Thương hiệu: {p.brand or 'Pancharm'}"
            + f"\n    Giá: {price} | Còn hàng: {'Có' if p.in_stock else 'Hết hàng'}"
            + (f"\n    Mô tả: {p.short_description}" if p.short_description else "")
            + f"\n    Chi tiết: {chunk_preview}"
        )
    return "\n".join(lines)


@lru_cache(maxsize=1)
def _get_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=settings.ANTHROPIC_MODEL_PRIMARY,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.7,
        max_tokens=1024,
    )


_PSYCH_STATE_LABELS = {
    PsychState.CURIOUS: "Khám phá (CURIOUS)",
    PsychState.INTERESTED: "Quan tâm (INTERESTED)",
    PsychState.HESITATION: "Phân vân (HESITATION)",
    PsychState.COMMITTED: "Sẵn sàng mua (COMMITTED)",
    PsychState.OBJECTING: "Phản bác (OBJECTING)",
}


def _build_synth_messages(state: ConversationState) -> tuple[list, str]:
    """
    @desc Xây dựng danh sách tin nhắn LLM từ trạng thái hội thoại để truyền vào Synth Agent
    @params state (ConversationState): Trạng thái hội thoại chứa sản phẩm, thông tin tâm lý và lịch sử tin nhắn
    @return tuple[list, str]: Tuple gồm danh sách tin nhắn LangChain và chuỗi user prompt để tái sử dụng
    """
    products = state.get("retrieved_products", [])
    scores = state.get("retrieval_scores", [])
    psych_state = state.get("psych_state", PsychState.CURIOUS)
    consult_strategy = state.get("consult_strategy", "Tư vấn chung")
    primary_concern = state.get("primary_concern")
    user_intent = state.get("user_intent", "")

    last_user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if getattr(msg, "type", "") == "human":
            last_user_msg = msg.content
            break

    product_context = _format_products_for_synth(products, scores)
    psych_label = _PSYCH_STATE_LABELS.get(psych_state, str(psych_state))

    user_prompt = (
        f"Tin nhắn khách hàng: {last_user_msg}\n\n"
        f"Ý định: {user_intent}\n\n"
        f"Trạng thái tâm lý: {psych_label}\n"
        f"Chiến lược tư vấn: {consult_strategy}\n"
        + (f"Rào cản chính: {primary_concern}\n" if primary_concern else "")
        + f"\n{product_context}\n\n"
        f"Hãy tạo phản hồi theo cấu trúc AIDA, phù hợp với trạng thái tâm lý và chiến lược trên."
    )

    return [
        SystemMessage(content=_SYNTH_SYSTEM),
        HumanMessage(content=user_prompt),
    ], user_prompt


async def synth_agent_node(state: ConversationState) -> dict:
    """
    @desc Node LangGraph bất đồng bộ của Synth Agent — tổng hợp phản hồi cuối dùng theo mô hình AIDA, hỗ trợ streaming token qua SSE
    @params state (ConversationState): Trạng thái hội thoại chứa sản phẩm, trạng thái tâm lý và chiến lược tư vấn
    @return dict: State delta gồm messages (AIMessage), final_response và error_state
    """
    t0 = time.perf_counter()
    products = state.get("retrieved_products", [])
    psych_state = state.get("psych_state", PsychState.CURIOUS)
    consult_strategy = state.get("consult_strategy", "Tư vấn chung")

    custom_logger.info(
        f"[Synth Agent] start | products={len(products)} | "
        f"psych={psych_state} | strategy='{consult_strategy[:40]}'"
    )

    messages, _ = _build_synth_messages(state)

    chunks: list[str] = []
    async for chunk in _get_llm().astream(messages):
        if chunk.content:
            chunks.append(chunk.content)

    response_text = "".join(chunks)
    latency = (time.perf_counter() - t0) * 1000
    custom_logger.info(
        f"[Synth Agent] complete | response_len={len(response_text)} chars | {latency:.0f}ms"
    )

    return {
        "messages": [AIMessage(content=response_text)],
        "final_response": response_text,
        "error_state": None,
    }
