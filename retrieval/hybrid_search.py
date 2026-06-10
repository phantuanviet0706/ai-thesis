from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from common.constants import (
    LAMBDA_DENSE,
    LAMBDA_SPARSE,
    LAMBDA_META,
    MMR_LAMBDA,
    TOP_K_INITIAL,
    TOP_K_FINAL,
)
from entity.product_doc import ProductDoc
from retrieval.chromadb_client import get_all_collections
from retrieval.embeddings import embed_query


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


def _bm25_scores(query_tokens: list[str], corpus: list[list[str]]) -> list[float]:
    if not corpus:
        return []
    bm25 = BM25Okapi(corpus)
    raw = bm25.get_scores(query_tokens)
    max_score = max(raw) if max(raw) > 0 else 1.0
    return [float(s / max_score) for s in raw]


def _meta_score(metadata: dict[str, Any], filters: dict[str, Any]) -> float:
    """Binary: 1.0 if all hard filters match, 0.0 otherwise."""
    for key, condition in filters.items():
        value = metadata.get(key)
        if value is None:
            return 0.0
        if isinstance(condition, dict):
            op, threshold = next(iter(condition.items()))
            if op == "$eq" and value != threshold:
                return 0.0
            if op == "$lte" and float(value) > float(threshold):
                return 0.0
            if op == "$gte" and float(value) < float(threshold):
                return 0.0
        elif value != condition:
            return 0.0
    return 1.0


def _mmr_select(
    query_vec: list[float],
    candidates: list[tuple[ProductDoc, list[float]]],
    k: int,
) -> list[ProductDoc]:
    """
    Maximal Marginal Relevance — balances relevance and diversity.
    Formula from thesis §3.2.2 Stage 3.
    """
    selected: list[ProductDoc] = []
    selected_vecs: list[list[float]] = []

    while len(selected) < k and candidates:
        best_idx, best_score = -1, float("-inf")
        for i, (doc, vec) in enumerate(candidates):
            relevance = _cosine_similarity(query_vec, vec)
            if selected_vecs:
                max_sim = max(_cosine_similarity(vec, sv) for sv in selected_vecs)
            else:
                max_sim = 0.0
            score = MMR_LAMBDA * relevance - (1 - MMR_LAMBDA) * max_sim
            if score > best_score:
                best_score, best_idx = score, i

        doc, vec = candidates.pop(best_idx)
        selected.append(doc)
        selected_vecs.append(vec)

    return selected


def hybrid_search(
    query: str,
    metadata_filters: dict[str, Any] | None = None,
    k: int = TOP_K_FINAL,
) -> list[ProductDoc]:
    """
    Three-stage hybrid retrieval for the KR Agent.

    Stage 1: Dense (cosine) + Sparse (BM25) + Meta filtering across all 3 collections.
    Stage 2: Composite score = 0.50·dense + 0.30·sparse + 0.20·meta
    Stage 3: MMR re-ranking to select diverse top-k results.
    """
    query_vec = embed_query(query)
    query_tokens = query.lower().split()
    filters = metadata_filters or {}

    raw_candidates: list[tuple[ProductDoc, list[float], float]] = []

    for collection_name, collection in get_all_collections().items():
        results = collection.query(
            query_embeddings=[query_vec],
            n_results=min(TOP_K_INITIAL, collection.count() or 1),
            include=["documents", "metadatas", "embeddings", "distances"],
        )

        docs_list = results.get("documents", [[]])[0]
        metas_list = results.get("metadatas", [[]])[0]
        embeds_list = results.get("embeddings", [[]])[0]
        distances_list = results.get("distances", [[]])[0]

        if not docs_list:
            continue

        # BM25 on this collection's corpus
        corpus_tokens = [d.lower().split() for d in docs_list]
        sparse_scores = _bm25_scores(query_tokens, corpus_tokens)

        for i, (chunk_text, meta, doc_vec, distance) in enumerate(
            zip(docs_list, metas_list, embeds_list, distances_list)
        ):
            dense_score = max(0.0, 1.0 - distance)
            sparse_score = sparse_scores[i] if i < len(sparse_scores) else 0.0
            meta_score = _meta_score(meta, filters)

            composite = (
                LAMBDA_DENSE * dense_score
                + LAMBDA_SPARSE * sparse_score
                + LAMBDA_META * meta_score
            )

            product = ProductDoc(
                id=meta.get("product_id", ""),
                name=meta.get("name", ""),
                sku=meta.get("sku"),
                short_description=meta.get("short_description"),
                description=meta.get("description"),
                category=meta.get("category"),
                brand=meta.get("brand"),
                unit_price=float(meta.get("unit_price", 0)),
                sale_price=meta.get("sale_price"),
                in_stock=bool(meta.get("in_stock", True)),
                attributes=meta.get("attributes"),
                collection_source=collection_name,
                chunk_text=chunk_text,
                composite_score=composite,
            )
            raw_candidates.append((product, doc_vec, composite))

    # Sort by composite score descending, take top TOP_K_INITIAL
    raw_candidates.sort(key=lambda x: x[2], reverse=True)
    top_candidates = [(doc, vec) for doc, vec, _ in raw_candidates[:TOP_K_INITIAL]]

    # MMR for diversity
    return _mmr_select(query_vec, top_candidates, k=k)
