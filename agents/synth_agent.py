"""
Synthesis Agent (Synth Agent) — final convergence point of the pipeline.

Immutable constraints (thesis §3.2.4):
  1. Factual Grounding: all product info from KR Agent only — zero hallucination tolerance
  2. Strategy Alignment: response structure conforms to Psych Agent's consult_strategy
  3. Natural Tone: friendly, culturally localized Vietnamese register

Response structure follows AIDA marketing model:
  Attention → Interest → Desire → Action (CTA calibrated to psych_state)
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from core.config import settings
from entity.product_doc import ProductDoc
from graph.state import ConversationState, PsychState
from utils.helper import read_file_contents

_SYNTH_SYSTEM = read_file_contents("resources/prompt/synth_agent.md")


def _format_products_for_synth(products: list[ProductDoc], scores: list[float]) -> str:
    if not products:
        return "Không có sản phẩm nào được tìm thấy."

    lines = ["=== SẢN PHẨM TÌM ĐƯỢC ==="]
    for i, (p, score) in enumerate(zip(products, scores), 1):
        price = f"{p.unit_price:,.0f}₫"
        if p.sale_price and p.sale_price < p.unit_price:
            price = f"~~{p.unit_price:,.0f}₫~~ → {p.sale_price:,.0f}₫"

        lines.append(
            f"\n[{i}] {p.name}"
            + (f" (SKU: {p.sku})" if p.sku else "")
            + f"\n    Danh mục: {p.category or 'N/A'} | Thương hiệu: {p.brand or 'Pancharm'}"
            + f"\n    Giá: {price} | Còn hàng: {'Có' if p.in_stock else 'Hết hàng'}"
            + (f"\n    Mô tả: {p.short_description}" if p.short_description else "")
            + (f"\n    Chi tiết: {p.chunk_text[:200]}..." if len(p.chunk_text) > 200 else f"\n    Chi tiết: {p.chunk_text}")
        )
    return "\n".join(lines)


def _build_synth_llm() -> ChatAnthropic:
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


def synth_agent_node(state: ConversationState) -> dict:
    """
    LangGraph node function for the Synth Agent.
    Returns a state delta with: final_response.
    After this node the graph transitions directly to END.
    """
    llm = _build_synth_llm()

    products = state.get("retrieved_products", [])
    scores = state.get("retrieval_scores", [])
    psych_state = state.get("psych_state", PsychState.CURIOUS)
    consult_strategy = state.get("consult_strategy", "Tư vấn chung")
    primary_concern = state.get("primary_concern")
    user_intent = state.get("user_intent", "")

    messages = state.get("messages", [])
    last_user_msg = ""
    for msg in reversed(messages):
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

    response = llm.invoke([
        SystemMessage(content=_SYNTH_SYSTEM),
        HumanMessage(content=user_prompt),
    ])

    return {
        "messages": [AIMessage(content=response.content)],
        "final_response": response.content,
        "error_state": None,
    }
