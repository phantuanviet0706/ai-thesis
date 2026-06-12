import time
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from constants.constants import (
    LAMBDA_DENSE,
    LAMBDA_SPARSE,
    LAMBDA_META,
    MMR_LAMBDA,
    TOP_K_INITIAL,
    TOP_K_FINAL,
)
from core.logger import custom_logger
from database.vector_db_manager import VectorDBManager
from entity.product_doc import ProductDoc
from retrieval.embeddings import embed_query


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    @desc Tính độ tương đồng cosine giữa hai vector — trả về 0.0 nếu một trong hai vector có độ dài bằng 0
    @params a (list[float]): Vector thứ nhất
    @params b (list[float]): Vector thứ hai
    @return float: Giá trị độ tương đồng cosine trong khoảng [-1.0, 1.0]
    """
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


def _bm25_scores(query_tokens: list[str], corpus: list[list[str]]) -> list[float]:
    """
    @desc Tính điểm BM25 chuẩn hóa cho từng tài liệu trong corpus so với câu truy vấn đã được token hóa
    @params query_tokens (list[str]): Danh sách token của câu truy vấn
    @params corpus (list[list[str]]): Danh sách tài liệu, mỗi tài liệu là danh sách token
    @return list[float]: Danh sách điểm BM25 đã chuẩn hóa về khoảng [0.0, 1.0]
    """
    if not corpus:
        return []
    bm25 = BM25Okapi(corpus)
    raw = bm25.get_scores(query_tokens)
    max_score = max(raw) if max(raw) > 0 else 1.0
    return [float(s / max_score) for s in raw]


def _meta_score(metadata: dict[str, Any], filters: dict[str, Any]) -> float:
    """
    @desc Tính điểm lọc metadata nhị phân — trả về 1.0 nếu tất cả điều kiện lọc được thỏa mãn, ngược lại trả về 0.0
    @params metadata (dict[str, Any]): Metadata của tài liệu cần kiểm tra
    @params filters (dict[str, Any]): Bộ điều kiện lọc cứng cần kiểm tra, hỗ trợ toán tử $eq, $lte, $gte
    @return float: 1.0 nếu tất cả điều kiện thỏa mãn, 0.0 nếu có ít nhất một điều kiện không thỏa mãn
    """
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
    @desc Chọn k tài liệu tốt nhất theo thuật toán Maximal Marginal Relevance (MMR) — cân bằng giữa độ liên quan và tính đa dạng
    @params query_vec (list[float]): Vector embedding của câu truy vấn
    @params candidates (list[tuple[ProductDoc, list[float]]]): Danh sách ứng viên gồm cặp (tài liệu, vector embedding)
    @params k (int): Số lượng tài liệu cần chọn
    @return list[ProductDoc]: Danh sách k tài liệu được chọn theo tiêu chí MMR
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
    @desc Thực hiện tìm kiếm lai ba giai đoạn cho KR Agent — kết hợp tìm kiếm dày đặc (dense), thưa (BM25) và lọc metadata, sau đó xếp hạng lại bằng MMR
    @params query (str): Câu truy vấn tìm kiếm của người dùng
    @params metadata_filters (dict[str, Any] | None): Bộ điều kiện lọc metadata tùy chọn
    @params k (int): Số lượng sản phẩm tối đa trả về sau khi xếp hạng MMR
    @return list[ProductDoc]: Danh sách sản phẩm phù hợp nhất sau khi qua toàn bộ pipeline tìm kiếm
    """
    t0 = time.perf_counter()
    filters = metadata_filters or {}
    custom_logger.info(
        f"[HybridSearch] start | k={k} | filters={list(filters.keys())} | "
        f"query_preview='{query[:80]}'"
    )

    query_vec = embed_query(query)
    query_tokens = query.lower().split()

    raw_candidates: list[tuple[ProductDoc, list[float], float]] = []

    for collection_name, collection in VectorDBManager().get_all_collections().items():
        col_count = collection.count() or 1
        results = collection.query(
            query_embeddings=[query_vec],
            n_results=min(TOP_K_INITIAL, col_count),
            include=["documents", "metadatas", "embeddings", "distances"],
        )

        docs_list = results.get("documents", [[]])[0]
        metas_list = results.get("metadatas", [[]])[0]
        embeds_list = results.get("embeddings", [[]])[0]
        distances_list = results.get("distances", [[]])[0]

        if not docs_list:
            custom_logger.debug(f"[HybridSearch] collection='{collection_name}' → 0 results")
            continue

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

        custom_logger.debug(
            f"[HybridSearch] collection='{collection_name}' → {len(docs_list)} hits"
        )

    custom_logger.info(f"[HybridSearch] raw_candidates={len(raw_candidates)} across 3 collections")

    raw_candidates.sort(key=lambda x: x[2], reverse=True)
    top_candidates = [(doc, vec) for doc, vec, _ in raw_candidates[:TOP_K_INITIAL]]

    results_final = _mmr_select(query_vec, top_candidates, k=k)

    latency = (time.perf_counter() - t0) * 1000
    custom_logger.info(
        f"[HybridSearch] complete | returned={len(results_final)} | {latency:.0f}ms"
    )
    return results_final
