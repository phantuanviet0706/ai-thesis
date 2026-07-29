"""
Knowledge Retrieval (KR) Agent — retrieval-first, reasoning-later.

Three-stage Graph RAG strategy (thesis §3.2.2):
  Stage 1: Query reformulation & expansion (Vietnamese synonyms + Graph RAG entities)
  Stage 2: Hybrid search (Dense 0.50 + BM25 0.30 + Metadata 0.20)
  Stage 3: Cross-encoder re-ranking + MMR diversity (top-5 passed to Synth Agent)
"""

import json

from agents.base_agent import BaseLLMAgent
from core.logger import custom_logger
from graph.state import ConversationState
from retrieval.graph_rag import enrich_query
from retrieval.hybrid_search import hybrid_search
from utils.helper import extract_json, format_customer_profile


def _last_human_text(messages: list) -> str:
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            return msg.content
    return str(messages[-1].content) if messages else ""


def _price_target_from_filter(price_condition) -> float | None:
    """
    @desc Rút ra 1 mức giá đại diện từ metadata_filters["price"] để làm mốc "gần nhất" khi fallback
    bỏ filter giá (xem hybrid_search price_proximity_target) — có cả $lte/$gte thì lấy trung điểm,
    chỉ có 1 trong 2 thì lấy đúng mức đó.
    @params price_condition: Giá trị filter price từ KR Agent LLM, dạng {"$lte": N}/{"$gte": N}/cả hai
    @return float | None: Mức giá mục tiêu, hoặc None nếu không parse được
    """
    if not isinstance(price_condition, dict):
        try:
            return float(price_condition)
        except (TypeError, ValueError):
            return None
    lte = price_condition.get("$lte")
    gte = price_condition.get("$gte")
    try:
        if lte is not None and gte is not None:
            return (float(lte) + float(gte)) / 2
        if lte is not None:
            return float(lte)
        if gte is not None:
            return float(gte)
    except (TypeError, ValueError):
        return None
    return None


class KRAgent(BaseLLMAgent):
    prompt_path = "resources/prompt/kr_agent.md"
    log_tag = "KR Agent"
    model_key = "FAST"
    max_tokens = 300

    def build_user_prompt(self, state: ConversationState) -> str:
        messages = state.get("messages", [])
        query = _last_human_text(messages)

        # Bổ sung context từ 2 lượt trước để KR Agent hiểu ngữ cảnh (mệnh, dịp, ngân sách đã đề cập)
        context_block = ""
        if messages and len(messages) > 1:
            prev_msgs = messages[:-1]
            recent_prev = prev_msgs[-4:]  # tối đa 2 lượt trước
            lines = []
            for msg in recent_prev:
                role = "Khách" if getattr(msg, "type", "") == "human" else "Bot"
                content = msg.content[:80] if len(msg.content) > 80 else msg.content
                lines.append(f"{role}: {content}")
            if lines:
                context_block = "Ngữ cảnh hội thoại trước:\n" + "\n".join(lines) + "\n\n"

        profile_line = format_customer_profile(state.get("extracted_info"))
        profile_block = f"{profile_line}\n\n" if profile_line else ""

        return f"{context_block}{profile_block}Câu hỏi mới nhất: {query}"

    def parse_response(self, raw_content: str, state: ConversationState) -> dict:
        messages = state.get("messages", [])
        query = _last_human_text(messages)
        graph_enriched = enrich_query(query)

        metadata_filters: dict = {}
        try:
            parsed = extract_json(raw_content)
            llm_enriched = parsed.get("enriched_query", query)
            metadata_filters = parsed.get("metadata_filters", {})
            metadata_filters = {k: v for k, v in metadata_filters.items() if v}
        except (json.JSONDecodeError, AttributeError, ValueError):
            llm_enriched = query
            custom_logger.warning("[KR Agent] Query expansion JSON parse failed, using raw query")

        enriched_query = f"{graph_enriched} {llm_enriched}".strip()
        custom_logger.info(
            f"[KR Agent] query expanded | filters={list(metadata_filters.keys())} | "
            f"query_len={len(enriched_query)}"
        )

        products = hybrid_search(query=enriched_query, metadata_filters=metadata_filters)

        # Nếu filter giá + mệnh/danh mục không ra sản phẩm nào, thử lại NGAY trong lượt này bằng
        # cách bỏ filter giá (giữ nguyên mệnh/danh mục — vẫn là hard filter, không nới) — tìm sản
        # phẩm đúng mệnh gần nhất về giá thay vì để Synth Agent hỏi khách nới giá từng bước qua
        # nhiều lượt hội thoại (dưới 2tr → 2-3tr → 3-5tr...), vốn gây trải nghiệm lặp vòng khó chịu.
        budget_relaxed = False
        if not products and "price" in metadata_filters:
            relaxed_filters = {k: v for k, v in metadata_filters.items() if k != "price"}
            price_target = _price_target_from_filter(metadata_filters["price"])
            custom_logger.info(
                f"[KR Agent] no results within budget — retrying without price filter "
                f"| price_proximity_target={price_target}"
            )
            # price_proximity_target: lấy sản phẩm giá CẬN TRÊN/CẬN DƯỚI gần ngân sách khách nêu
            # nhất (tối đa TOP_K_FINAL=5, tối thiểu tùy số lượng thực có) thay vì sản phẩm điểm
            # liên quan/đa dạng cao nhất bất kể giá — để Synth Agent có ngay vài lựa chọn gần đúng
            # ngân sách trình bày cho khách chọn, thay vì phải hỏi lại khách có muốn nới giá không.
            products = hybrid_search(
                query=enriched_query,
                metadata_filters=relaxed_filters,
                price_proximity_target=price_target,
            )
            budget_relaxed = bool(products)

        scores = [p.composite_score for p in products]
        custom_logger.info(
            f"[KR Agent] products={len(products)} | top_score={max(scores, default=0.0):.3f} | "
            f"budget_relaxed={budget_relaxed}"
        )

        # Không ghi "next_node"/"error_state" ở nhánh thành công: cạnh kr_agent→orchestrator
        # là static edge (không đọc next_node), và orchestrator đã luôn set error_state=None
        # ngay trước khi route sang đây nên ghi lại là dư thừa. Quan trọng hơn: nếu ghi, khi
        # kr_agent chạy song song với psych_agent (cả 2 cùng ghi field không reducer trong
        # 1 superstep) sẽ gây LangGraph InvalidUpdateError.
        return {
            "retrieved_products": products,
            "retrieval_scores": scores,
            "budget_relaxed": budget_relaxed,
        }

    def on_error(self, exc: Exception, state: ConversationState) -> dict:
        custom_logger.error(f"[KR Agent] error: {exc}", exc_info=True)
        return {
            "retrieved_products": [],
            "retrieval_scores": [],
            "budget_relaxed": False,
            "error_state": f"KR Agent error: {exc}",
        }


kr_agent_node = KRAgent()
