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

from constants.constants import COLLECTION_TRAINING_SUCCESS
from core.config import settings
from core.logger import custom_logger
from database.vector_db_manager import VectorDBManager
from entity.product_doc import ProductDoc
from graph.state import ConversationState, PsychState
from retrieval.embeddings import embed_query
from utils.helper import read_file_contents

_MIN_SUCCESS_EXAMPLES = 3   # chỉ retrieval khi có đủ ≥ 3 session thành công để ví dụ có giá trị

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
        temperature=0.3,  # factual grounding: thấp để giảm hallucination, vẫn đủ tự nhiên
        max_tokens=400,
    )


_PSYCH_STATE_LABELS = {
    PsychState.CURIOUS: "Khám phá (CURIOUS)",
    PsychState.INTERESTED: "Quan tâm (INTERESTED)",
    PsychState.HESITATION: "Phân vân (HESITATION)",
    PsychState.COMMITTED: "Sẵn sàng mua (COMMITTED)",
    PsychState.OBJECTING: "Phản bác (OBJECTING)",
}


def _get_similar_success_example(query: str) -> str:
    """
    Truy xuất 1 transcript session thành công tương tự từ ChromaDB để dùng làm few-shot example.
    Chỉ hoạt động khi collection có ≥ _MIN_SUCCESS_EXAMPLES bản ghi (tránh dùng dữ liệu quá ít).
    Trả về chuỗi rỗng nếu không có dữ liệu hoặc xảy ra lỗi.
    """
    try:
        vdb = VectorDBManager()
        col = vdb.get_collection(COLLECTION_TRAINING_SUCCESS)
        if col.count() < _MIN_SUCCESS_EXAMPLES:
            return ""

        results = col.query(
            query_embeddings=[embed_query(query)],
            n_results=1,
        )
        docs = (results.get("documents") or [[]])[0]
        if not docs:
            return ""

        transcript = docs[0]
        # Giới hạn 600 ký tự để không làm phình prompt
        if len(transcript) > 600:
            transcript = transcript[:597] + "..."

        return (
            "\n=== VÍ DỤ PHIÊN TƯ VẤN THÀNH CÔNG TƯƠNG TỰ (tham khảo tone & flow) ===\n"
            + transcript
            + "\n=== KẾT THÚC VÍ DỤ ===\n"
        )
    except Exception as exc:
        custom_logger.debug(f"[Synth] success example retrieval skipped: {exc}")
        return ""


def _format_history_for_synth(messages: list, max_turns: int = 3) -> str:
    """Lấy N lượt hội thoại gần nhất (trừ tin nhắn cuối cùng) để đưa vào context Synth."""
    history = messages[:-1]  # bỏ tin nhắn hiện tại (đã được truyền riêng)
    recent = history[-(max_turns * 2):]
    if not recent:
        return ""
    lines = []
    for msg in recent:
        role = "Khách" if getattr(msg, "type", "") == "human" else "Tư vấn viên"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)


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
    all_messages = state.get("messages", [])

    last_user_msg = ""
    for msg in reversed(all_messages):
        if getattr(msg, "type", "") == "human":
            last_user_msg = msg.content
            break

    # Số lượt khách đã nhắn (để biết đây là lượt mấy)
    turn_number = sum(1 for m in all_messages if getattr(m, "type", "") == "human")
    history_text = _format_history_for_synth(all_messages, max_turns=3)
    product_context = _format_products_for_synth(products, scores)
    psych_label = _PSYCH_STATE_LABELS.get(psych_state, str(psych_state))

    history_section = f"Lịch sử hội thoại trước:\n{history_text}\n\n" if history_text else ""
    continuation_hint = "" if turn_number <= 1 else "KHÔNG lặp lại lời chào. Tiếp tục cuộc hội thoại tự nhiên.\n"
    success_example = _get_similar_success_example(last_user_msg)

    user_prompt = (
        f"{history_section}"
        f"Tin nhắn mới nhất của khách: {last_user_msg}\n\n"
        f"Ý định: {user_intent}\n"
        f"Lượt thứ: {turn_number}\n\n"
        f"Trạng thái tâm lý: {psych_label}\n"
        f"Chiến lược tư vấn: {consult_strategy}\n"
        + (f"Rào cản chính: {primary_concern}\n" if primary_concern else "")
        + f"\n{product_context}\n"
        + success_example
        + f"\n{continuation_hint}"
        f"Viết tin nhắn tư vấn ngắn gọn, đúng trọng tâm, theo giới hạn từ của trạng thái tâm lý."
    )

    return [
        SystemMessage(content=[{"type": "text", "text": _SYNTH_SYSTEM, "cache_control": {"type": "ephemeral"}}]),
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
