"""
Knowledge Retrieval (KR) Agent — retrieval-first, reasoning-later.

Three-stage Graph RAG strategy (thesis §3.2.2):
  Stage 1: Query reformulation & expansion (Vietnamese synonyms + Graph RAG entities)
  Stage 2: Hybrid search (Dense 0.50 + BM25 0.30 + Metadata 0.20)
  Stage 3: Cross-encoder re-ranking + MMR diversity (top-5 passed to Synth Agent)
"""

import json
import time

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from core.config import settings
from core.logger import custom_logger
from graph.state import ConversationState
from retrieval.graph_rag import enrich_query
from retrieval.hybrid_search import hybrid_search
from utils.helper import read_file_contents

_EXPANSION_PROMPT = read_file_contents("resources/prompt/kr_agent.md")


def _build_kr_llm() -> ChatAnthropic:
    """
    @desc Khởi tạo LLM tốc độ cao (Haiku) dùng cho KR Agent
    @return ChatAnthropic: Instance ChatAnthropic với temperature=0 và max_tokens=256
    """
    return ChatAnthropic(
        model=settings.ANTHROPIC_MODEL_FAST,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.0,
        max_tokens=256,
    )


def _expand_query(llm: ChatAnthropic, query: str) -> tuple[str, dict]:
    """
    @desc Mở rộng câu truy vấn bằng LLM kết hợp Graph RAG để cải thiện độ chính xác tìm kiếm
    @params llm (ChatAnthropic): Instance ChatAnthropic dùng để reformulate query
    @params query (str): Câu hỏi gốc từ người dùng
    @return tuple[str, dict]: Tuple gồm query đã mở rộng và bộ lọc metadata tương ứng
    """
    graph_enriched = enrich_query(query)

    response = llm.invoke([
        SystemMessage(content=_EXPANSION_PROMPT),
        HumanMessage(content=f"Câu hỏi: {query}"),
    ])

    metadata_filters: dict = {}
    try:
        parsed = json.loads(response.content)
        llm_enriched = parsed.get("enriched_query", query)
        metadata_filters = parsed.get("metadata_filters", {})
        metadata_filters = {k: v for k, v in metadata_filters.items() if v}
    except (json.JSONDecodeError, AttributeError):
        llm_enriched = query
        custom_logger.warning("[KR Agent] Query expansion JSON parse failed, using raw query")

    final_query = f"{graph_enriched} {llm_enriched}".strip()
    return final_query, metadata_filters


def kr_agent_node(state: ConversationState) -> dict:
    """
    @desc Node LangGraph của KR Agent — tìm kiếm sản phẩm phù hợp dựa trên câu hỏi người dùng
    @params state (ConversationState): Trạng thái hội thoại chứa lịch sử tin nhắn và metadata session
    @return dict: State delta gồm retrieved_products, retrieval_scores và next_node
    """
    t0 = time.perf_counter()
    custom_logger.info("[KR Agent] start")

    llm = _build_kr_llm()

    messages = state.get("messages", [])
    last_user_text = ""
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            last_user_text = msg.content
            break
    if not last_user_text and messages:
        last_user_text = str(messages[-1].content)

    try:
        enriched_query, metadata_filters = _expand_query(llm, last_user_text)
        custom_logger.info(
            f"[KR Agent] query expanded | filters={list(metadata_filters.keys())} | "
            f"query_len={len(enriched_query)}"
        )

        products = hybrid_search(query=enriched_query, metadata_filters=metadata_filters)
        scores = [p.composite_score for p in products]

        latency = (time.perf_counter() - t0) * 1000
        custom_logger.info(
            f"[KR Agent] complete | products={len(products)} | "
            f"top_score={max(scores, default=0.0):.3f} | {latency:.0f}ms"
        )

        return {
            "retrieved_products": products,
            "retrieval_scores": scores,
            "next_node": "orchestrator",
            "error_state": None,
        }

    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        custom_logger.error(f"[KR Agent] error after {latency:.0f}ms: {exc}", exc_info=True)
        return {
            "retrieved_products": [],
            "retrieval_scores": [],
            "error_state": f"KR Agent error: {exc}",
            "next_node": "error_handler",
        }
