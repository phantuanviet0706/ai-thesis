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
from utils.helper import extract_json


def _last_human_text(messages: list) -> str:
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            return msg.content
    return str(messages[-1].content) if messages else ""


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

        return f"{context_block}Câu hỏi mới nhất: {query}"

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
        scores = [p.composite_score for p in products]
        custom_logger.info(
            f"[KR Agent] products={len(products)} | top_score={max(scores, default=0.0):.3f}"
        )

        # Không ghi "next_node"/"error_state" ở nhánh thành công: cạnh kr_agent→orchestrator
        # là static edge (không đọc next_node), và orchestrator đã luôn set error_state=None
        # ngay trước khi route sang đây nên ghi lại là dư thừa. Quan trọng hơn: nếu ghi, khi
        # kr_agent chạy song song với psych_agent (cả 2 cùng ghi field không reducer trong
        # 1 superstep) sẽ gây LangGraph InvalidUpdateError.
        return {
            "retrieved_products": products,
            "retrieval_scores": scores,
        }

    def on_error(self, exc: Exception, state: ConversationState) -> dict:
        custom_logger.error(f"[KR Agent] error: {exc}", exc_info=True)
        return {
            "retrieved_products": [],
            "retrieval_scores": [],
            "error_state": f"KR Agent error: {exc}",
        }


kr_agent_node = KRAgent()
