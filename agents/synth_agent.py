"""
Synthesis Agent (Synth Agent) — final convergence point of the pipeline.

Immutable constraints (thesis §3.2.4):
  1. Factual Grounding: all product info from KR Agent only — zero hallucination tolerance
  2. Strategy Alignment: response structure conforms to Psych Agent's consult_strategy
  3. Natural Tone: friendly, culturally localized Vietnamese register

Consultative-first: no hard word cap, no rigid branch script — the agent reasons about
psych_state/consult_strategy/primary_concern like a genuine advisor. When the customer
has no specific product insight yet, it proactively surfaces a hot or profile-matched
product (see resources/prompt/synth_agent.md) instead of only asking questions.
"""

import time
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from constants.constants import COLLECTION_TRAINING_SUCCESS, FALLBACK_ERROR_RESPONSE
from core.llm_factory import build_chat_model, build_system_message
from core.logger import custom_logger
from database.vector_db_manager import VectorDBManager
from entity.product_doc import ProductDoc
from graph.state import ConversationState, PsychState
from retrieval.embeddings import embed_query
from utils.helper import format_customer_profile, read_file_contents, resolve_address_style

_MIN_SUCCESS_EXAMPLES = 3   # chỉ retrieval khi có đủ ≥ 3 session thành công để ví dụ có giá trị

_SYNTH_SYSTEM = read_file_contents("resources/prompt/synth_agent.md")

# Cụm từ ngụ ý việc tra cứu catalog CHƯA xảy ra — sai khi retrieved_products đã có sẵn,
# vì KR Agent luôn tra cứu xong trước khi Synth nhận context (xem synth_agent.md rule 42).
_CATALOG_HEDGE_PHRASES = (
    "kiểm tra lại catalog",
    "kiểm tra lại kho",
    "kiểm tra lại xem còn hàng",
    "kiểm tra lại xem đúng mẫu",
    "để em xem lại kho",
    "để em hỏi lại bên kho",
    "để mình kiểm tra lại",
    "để em kiểm tra lại",
)


def _has_contradictory_catalog_hedge(response_text: str, has_products: bool) -> bool:
    """Phát hiện phản hồi tự mâu thuẫn: context đã có sản phẩm nhưng vẫn nói như thể
    tra cứu catalog chưa xảy ra (vd 'cần kiểm tra lại catalog nhé')."""
    if not has_products:
        return False
    lowered = response_text.lower()
    return any(phrase in lowered for phrase in _CATALOG_HEDGE_PHRASES)


def _format_products_for_synth(
    products: list[ProductDoc],
    scores: list[float] | None = None,
    header: str = "=== SẢN PHẨM TÌM ĐƯỢC ===",
) -> str:
    """
    @desc Định dạng danh sách sản phẩm thành chuỗi văn bản để đưa vào context của Synth Agent
    @params products (list[ProductDoc]): Danh sách sản phẩm (tối đa 5 sản phẩm đầu, khớp TOP_K_FINAL
    — đủ để Synth Agent trình bày tối thiểu 5 lựa chọn khi khách đang tìm hiểu 1 dòng sản phẩm, xem
    "Tư Vấn Chủ Động" trong resources/prompt/synth_agent.md)
    @params scores (list[float] | None): Điểm composite tương ứng (nếu có) — chỉ dùng để tính toán nội bộ,
    không hiển thị trong context nên có thể bỏ qua khi định dạng previous_turn_products
    @params header (str): Dòng tiêu đề của block, phân biệt sản phẩm lượt này với lượt trước
    @return str: Chuỗi văn bản mô tả sản phẩm đã được định dạng, hoặc thông báo không tìm thấy sản phẩm
    """
    if not products:
        return f"{header}\n(không có)"

    scores = scores or []
    lines = [header]
    for i, p in enumerate(products[:5], 1):
        price = f"{p.unit_price:,.0f}₫"
        if p.sale_price and p.sale_price < p.unit_price:
            price = f"~~{p.unit_price:,.0f}₫~~ → {p.sale_price:,.0f}₫"

        chunk_preview = p.chunk_text[:120] + "..." if len(p.chunk_text) > 120 else p.chunk_text

        element = (p.attributes or {}).get("element") if p.attributes else None

        lines.append(
            f"\n[{i}] {p.name}"
            + (f" (SKU: {p.sku})" if p.sku else "")
            + (" 🔥 ĐANG HOT (bán chạy)" if p.is_hot else "")
            + f"\n    Danh mục: {p.category or 'N/A'} | Thương hiệu: {p.brand or 'Pancharm'}"
            + f"\n    Giá: {price} | Còn hàng: {'Có' if p.in_stock else 'Hết hàng'}"
            + (f"\n    Hợp mệnh: {element}" if element else "")
            + (f"\n    Mô tả: {p.short_description}" if p.short_description else "")
            + f"\n    Chi tiết: {chunk_preview}"
        )
    return "\n".join(lines)


@lru_cache(maxsize=1)
def _get_llm() -> BaseChatModel:
    return build_chat_model(
        "PRIMARY",
        temperature=0.3,  # factual grounding: thấp để giảm hallucination, vẫn đủ tự nhiên
        # Không còn giới hạn cứng "tối đa 20 từ" — đủ token cho một lời tư vấn tự nhiên,
        # trọn ý, kể cả khi liệt kê tối thiểu 5 lựa chọn sản phẩm (xem nguyên tắc #2 trong
        # resources/prompt/synth_agent.md), nhưng vẫn chặn trần để tránh trả lời lan man
        # vô hạn và giữ latency ổn định.
        max_tokens=600,
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
    budget_relaxed = state.get("budget_relaxed", False)
    previous_products = state.get("previous_turn_products", [])
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
    product_context = _format_products_for_synth(products, scores, header="=== SẢN PHẨM TÌM ĐƯỢC LƯỢT NÀY ===")
    previous_product_context = _format_products_for_synth(
        previous_products, header="=== SẢN PHẨM ĐÃ GỢI Ý LƯỢT TRƯỚC ==="
    )
    psych_label = _PSYCH_STATE_LABELS.get(psych_state, str(psych_state))

    history_section = f"Lịch sử hội thoại trước:\n{history_text}\n\n" if history_text else ""
    continuation_hint = "" if turn_number <= 1 else "KHÔNG lặp lại lời chào. Tiếp tục cuộc hội thoại tự nhiên.\n"
    success_example = _get_similar_success_example(last_user_msg)
    profile_line = format_customer_profile(state.get("extracted_info"))
    profile_section = f"{profile_line}\n" if profile_line else ""
    address_style = resolve_address_style(all_messages)
    budget_relaxed_note = (
        "\nLƯU Ý QUAN TRỌNG: Không có sản phẩm nào khớp đúng ngân sách khách vừa nêu — các sản "
        "phẩm trong '=== SẢN PHẨM TÌM ĐƯỢC LƯỢT NÀY ===' đã VƯỢT ngân sách đó (nhưng vẫn đúng "
        "mệnh/danh mục khách yêu cầu, đã tra cứu xong). Nói thẳng giá thực tế ngay, KHÔNG hỏi khách "
        "có muốn nới giá lên mức nào khác — hệ thống đã tự tìm sản phẩm đúng mệnh gần nhất về giá rồi.\n"
        if budget_relaxed
        else ""
    )

    user_prompt = (
        f"{history_section}"
        f"Tin nhắn mới nhất của khách: {last_user_msg}\n\n"
        f"Ý định: {user_intent}\n"
        f"Lượt thứ: {turn_number}\n\n"
        f"Xưng hô lượt này: {address_style}\n"
        f"Trạng thái tâm lý: {psych_label}\n"
        f"Chiến lược tư vấn: {consult_strategy}\n"
        + (f"Rào cản chính: {primary_concern}\n" if primary_concern else "")
        + profile_section
        + budget_relaxed_note
        + f"\n{previous_product_context}\n"
        + f"\n{product_context}\n"
        + success_example
        + f"\n{continuation_hint}"
        f"Viết tin nhắn tư vấn ngắn gọn, đúng trọng tâm, theo giới hạn từ của trạng thái tâm lý."
    )

    return [
        build_system_message(_SYNTH_SYSTEM),
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
    try:
        async for chunk in _get_llm().astream(messages):
            if chunk.text:
                chunks.append(chunk.text)
    except Exception as exc:
        # Synth Agent nối thẳng ra END (không qua error_handler như các agent khác), nên phải
        # tự trả fallback khi LLM call thất bại giữa chừng (provider quá tải, timeout, rate
        # limit...) — nếu không khách sẽ không nhận được phản hồi nào cả.
        latency = (time.perf_counter() - t0) * 1000
        custom_logger.error(
            f"[Synth Agent] LLM stream failed | {latency:.0f}ms | {exc}", exc_info=True
        )
        fallback = f"{FALLBACK_ERROR_RESPONSE} [Debug: Synth Agent lỗi: {exc}]"
        return {
            "messages": [AIMessage(content=fallback)],
            "final_response": fallback,
            "error_state": None,
        }

    response_text = "".join(chunks)

    if _has_contradictory_catalog_hedge(response_text, bool(products)):
        custom_logger.warning(
            "[Synth Agent] contradictory catalog hedge with non-empty retrieved_products — regenerating once"
        )
        correction_messages = messages + [
            AIMessage(content=response_text),
            HumanMessage(
                content=(
                    "Câu trả lời trên ngụ ý bạn CHƯA tra cứu catalog, nhưng "
                    "'=== SẢN PHẨM TÌM ĐƯỢC LƯỢT NÀY ===' đã có sẵn sản phẩm cụ thể. Viết lại: trình bày "
                    "thẳng các sản phẩm đó, KHÔNG dùng bất kỳ cụm nào ngụ ý cần kiểm tra lại catalog/kho/tồn hàng."
                )
            ),
        ]
        try:
            chunks = []
            async for chunk in _get_llm().astream(correction_messages):
                if chunk.text:
                    chunks.append(chunk.text)
            response_text = "".join(chunks)
        except Exception as exc:
            # Regenerate thất bại — giữ nguyên response_text gốc thay vì làm hỏng cả lượt trả
            # lời (response gốc dù có hedge mâu thuẫn vẫn còn hữu ích hơn là không trả lời gì).
            custom_logger.warning(
                f"[Synth Agent] correction regenerate failed, keeping original response | {exc}"
            )

    latency = (time.perf_counter() - t0) * 1000
    word_count = len(response_text.split())
    custom_logger.info(
        f"[Synth Agent] complete | words={word_count} | "
        f"response_len={len(response_text)} chars | {latency:.0f}ms"
    )

    return {
        "messages": [AIMessage(content=response_text)],
        "final_response": response_text,
        "error_state": None,
    }
