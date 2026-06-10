"""
Knowledge Retrieval (KR) Agent — retrieval-first, reasoning-later.

Three-stage Graph RAG strategy (thesis §3.2.2):
  Stage 1: Query reformulation & expansion (Vietnamese synonyms + Graph RAG entities)
  Stage 2: Hybrid search (Dense 0.50 + BM25 0.30 + Metadata 0.20)
  Stage 3: Cross-encoder re-ranking + MMR diversity (top-5 passed to Synth Agent)
"""

import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from core.config import settings
from graph.state import ConversationState
from retrieval.graph_rag import enrich_query
from retrieval.hybrid_search import hybrid_search
from utils.helper import read_file_contents

_EXPANSION_PROMPT = read_file_contents("resources/prompt/kr_agent.md")

def _build_kr_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=settings.ANTHROPIC_MODEL_FAST,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.0,
        max_tokens=256,
    )


def _expand_query(llm: ChatAnthropic, query: str) -> tuple[str, dict]:
    """Stage 1: Query reformulation via LLM + Graph RAG entity traversal."""
    # Graph RAG traversal
    graph_enriched = enrich_query(query)

    # LLM synonym expansion
    response = llm.invoke([
        SystemMessage(content=_EXPANSION_PROMPT),
        HumanMessage(content=f"Câu hỏi: {query}"),
    ])

    metadata_filters: dict = {}
    try:
        parsed = json.loads(response.content)
        llm_enriched = parsed.get("enriched_query", query)
        metadata_filters = parsed.get("metadata_filters", {})
        # Remove null/empty filter values
        metadata_filters = {k: v for k, v in metadata_filters.items() if v}
    except (json.JSONDecodeError, AttributeError):
        llm_enriched = query

    # Merge graph enrichment + LLM expansion
    final_query = f"{graph_enriched} {llm_enriched}".strip()
    return final_query, metadata_filters


def kr_agent_node(state: ConversationState) -> dict:
    """
    LangGraph node function for the KR Agent.
    Returns a state delta with: retrieved_products, retrieval_scores, next_node.
    """
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

        # Stage 2+3: Hybrid search + MMR (implemented in hybrid_search module)
        products = hybrid_search(
            query=enriched_query,
            metadata_filters=metadata_filters,
        )

        scores = [p.composite_score for p in products]

        return {
            "retrieved_products": products,
            "retrieval_scores": scores,
            "next_node": "orchestrator",  # always returns to orchestrator
            "error_state": None,
        }

    except Exception as exc:
        return {
            "retrieved_products": [],
            "retrieval_scores": [],
            "error_state": f"KR Agent error: {exc}",
            "next_node": "error_handler",
        }
