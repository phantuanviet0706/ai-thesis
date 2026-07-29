import json
import time
import unicodedata
from typing import Any

import chromadb.errors
import numpy as np
from rank_bm25 import BM25Okapi

from constants.constants import (
    LAMBDA_DENSE,
    LAMBDA_SPARSE,
    LAMBDA_META,
    MMR_LAMBDA,
    POPULARITY_BOOST,
    TOP_K_INITIAL,
    TOP_K_FINAL,
)
from core.logger import custom_logger
from database.vector_db_manager import VectorDBManager
from entity.product_doc import ProductDoc
from retrieval.embeddings import embed_query


def _tokenize_vi(text: str) -> list[str]:
    """
    NFC normalize + lowercase trước khi split — tránh mismatch do encoding dấu tiếng Việt.
    Ví dụ: "vòng tay" (precomposed) và "vòng tay" (decomposed) sẽ match được nhau.
    """
    return unicodedata.normalize("NFC", text.lower()).split()


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


# KR Agent phát ra filter key "price" (xem resources/prompt/kr_agent.md) nhưng field thật trong
# metadata Chroma là "unit_price" (xem scripts/seed_vectordb.py::_product_meta) — không map lại thì
# metadata.get("price") luôn None, khiến điều kiện giá bị bỏ qua hoàn toàn trong _meta_score/_passes_hard_filters
# (bug cũ: filter giá coi như không tồn tại, sản phẩm sai giá vẫn lọt vào kết quả).
_FILTER_KEY_TO_METADATA_FIELD = {"price": "unit_price"}

# category/price/element (mệnh) là các tiêu chí khách thường nêu RÕ RÀNG (xem
# resources/prompt/synth_agent.md nguyên tắc #2 "BÁM SÁT ĐÚNG TIÊU CHÍ") — phải lọc CỨNG (loại
# hẳn), không cho điểm 1 phần như trước, để không có sản phẩm sai danh mục/lệch giá/khác mệnh
# lọt vào top-k gợi ý cho khách.
_HARD_FILTER_KEYS = ("category", "price", "element")


def _check_element_condition(value: str, condition: Any) -> bool:
    """
    @desc So khớp mệnh ngũ hành kiểu "chứa trong" — field attributes.element trong dữ liệu có thể
    là 1 mệnh đơn ("Kim") hoặc nhiều mệnh cách nhau bởi dấu phẩy ("Kim, Thổ", thứ tự không cố định),
    nên không thể so bằng $eq nguyên chuỗi — phải kiểm tra mệnh khách nêu có nằm trong danh sách đó không.
    @params value (str): Giá trị element thô từ metadata, vd "Kim, Thổ"
    @params condition (Any): Điều kiện lọc, dạng {"$eq": "Kim"} hoặc chuỗi "Kim"
    @return bool: True nếu mệnh khách nêu nằm trong danh sách mệnh của sản phẩm
    """
    threshold = condition.get("$eq") if isinstance(condition, dict) else condition
    if not threshold:
        return False
    wanted = str(threshold).strip().lower()
    parts = [p.strip().lower() for p in str(value).split(",")]
    return wanted in parts


def _check_condition(value: Any, condition: Any) -> bool:
    """
    @desc Kiểm tra 1 giá trị metadata có thỏa 1 điều kiện filter không (hỗ trợ $eq/$lte/$gte hoặc so sánh trực tiếp)
    @params value (Any): Giá trị thực tế lấy từ metadata
    @params condition (Any): Điều kiện lọc — dict {"$eq"/"$lte"/"$gte": threshold} hoặc giá trị so sánh trực tiếp
    @return bool: True nếu giá trị thỏa điều kiện
    """
    if isinstance(condition, dict):
        op, threshold = next(iter(condition.items()))
        try:
            if op == "$eq":
                return str(value).strip().lower() == str(threshold).strip().lower()
            if op == "$lte":
                return float(value) <= float(threshold)
            if op == "$gte":
                return float(value) >= float(threshold)
        except (TypeError, ValueError):
            return False
        return False
    return str(value).strip().lower() == str(condition).strip().lower()


def _passes_hard_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
    """
    @desc Loại HẲN candidate nếu không khớp category/price/element (mệnh) khi khách đã nêu rõ các
    tiêu chí này — không cho lọt vào kết quả dưới dạng "gợi ý tương tự" nữa (xem
    resources/prompt/synth_agent.md).
    @params metadata (dict[str, Any]): Metadata thô của candidate
    @params filters (dict[str, Any]): Bộ điều kiện lọc từ KR Agent
    @return bool: True nếu candidate được giữ lại (thỏa mọi hard filter có mặt), False nếu bị loại
    """
    for key in _HARD_FILTER_KEYS:
        if key not in filters:
            continue
        field = _FILTER_KEY_TO_METADATA_FIELD.get(key, key)
        value = metadata.get(field)
        if value is None or value == "":
            return False
        if key == "element":
            if not _check_element_condition(value, filters[key]):
                return False
        elif not _check_condition(value, filters[key]):
            return False
    return True


def _meta_score(metadata: dict[str, Any], filters: dict[str, Any]) -> float:
    """
    @desc Tính điểm lọc metadata theo kiểu soft scoring cho các tiêu chí KHÔNG thuộc hard filter
    (vd in_stock) — trả về tỷ lệ điều kiện thỏa mãn. category/price đã được lọc cứng ở
    _passes_hard_filters nên không cần tính lại ở đây.
    @params metadata (dict[str, Any]): Metadata của tài liệu cần kiểm tra
    @params filters (dict[str, Any]): Bộ điều kiện lọc hỗ trợ toán tử $eq, $lte, $gte
    @return float: Tỷ lệ [0.0, 1.0] — số điều kiện thỏa / tổng điều kiện (loại trừ hard filter keys)
    """
    soft_filters = {k: v for k, v in filters.items() if k not in _HARD_FILTER_KEYS}
    if not soft_filters:
        return 1.0

    matches = 0
    for key, condition in soft_filters.items():
        field = _FILTER_KEY_TO_METADATA_FIELD.get(key, key)
        value = metadata.get(field)
        if value is None:
            continue
        if _check_condition(value, condition):
            matches += 1

    return matches / len(soft_filters)


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
    price_proximity_target: float | None = None,
) -> list[ProductDoc]:
    """
    @desc Thực hiện tìm kiếm lai ba giai đoạn cho KR Agent — kết hợp tìm kiếm dày đặc (dense), thưa (BM25) và lọc metadata, sau đó xếp hạng lại bằng MMR
    @params query (str): Câu truy vấn tìm kiếm của người dùng
    @params metadata_filters (dict[str, Any] | None): Bộ điều kiện lọc metadata tùy chọn
    @params k (int): Số lượng sản phẩm tối đa trả về sau khi xếp hạng
    @params price_proximity_target (float | None): Nếu có — dùng cho fallback "không đúng ngân
    sách" (xem agents/kr_agent.py::budget_relaxed): bỏ qua MMR/composite score, sort candidates
    theo khoảng cách giá TUYỆT ĐỐI tới mức này (gần nhất trước, không phân biệt cao/thấp hơn ngân
    sách) rồi lấy top-k — vì mục tiêu của fallback này là "sản phẩm giá cận trên/cận dưới gần ngân
    sách khách nêu nhất", không phải độ liên quan ngữ nghĩa/đa dạng như tìm kiếm thông thường.
    @return list[ProductDoc]: Danh sách sản phẩm phù hợp nhất sau khi qua toàn bộ pipeline tìm kiếm
    """
    t0 = time.perf_counter()
    filters = metadata_filters or {}
    custom_logger.info(
        f"[HybridSearch] start | k={k} | filters={list(filters.keys())} | "
        f"query_preview='{query[:80]}'"
    )

    query_vec = embed_query(query)
    query_tokens = _tokenize_vi(query)

    raw_candidates: list[tuple[ProductDoc, list[float], float]] = []

    for collection_name, collection in VectorDBManager().get_all_collections().items():
        col_count = collection.count() or 1
        try:
            results = collection.query(
                query_embeddings=[query_vec],
                n_results=min(TOP_K_INITIAL, col_count),
                include=["documents", "metadatas", "embeddings", "distances"],
            )
        except chromadb.errors.InternalError as exc:
            # "Error creating hnsw segment reader: Nothing found on disk" — process này đang giữ
            # PersistentClient/Collection handle cũ, không khớp dữ liệu thật trên disk (thường do
            # 1 process khác — vd script seed_vectordb.py — ghi vào cùng CHROMA_PATH trong lúc
            # process này đang chạy). Reset client rồi lấy lại collection MỚI, thử lại đúng 1 lần
            # trước khi để lỗi văng ra ngoài cho KRAgent.on_error xử lý (xem agents/kr_agent.py).
            if "disk" not in str(exc).lower() and "segment" not in str(exc).lower():
                raise
            custom_logger.warning(
                f"[HybridSearch] collection='{collection_name}' stale segment handle — "
                f"resetting client and retrying once | error={exc}"
            )
            VectorDBManager().reset_client()
            collection = VectorDBManager().get_collection(collection_name)
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

        corpus_tokens = [_tokenize_vi(d) for d in docs_list]
        sparse_scores = _bm25_scores(query_tokens, corpus_tokens)

        for i, (chunk_text, meta, doc_vec, distance) in enumerate(
            zip(docs_list, metas_list, embeds_list, distances_list)
        ):
            if not _passes_hard_filters(meta, filters):
                continue

            dense_score = max(0.0, 1.0 - distance)
            sparse_score = sparse_scores[i] if i < len(sparse_scores) else 0.0
            meta_score = _meta_score(meta, filters)
            is_hot = bool(meta.get("is_hot", False))

            composite = (
                LAMBDA_DENSE * dense_score
                + LAMBDA_SPARSE * sparse_score
                + LAMBDA_META * meta_score
                + (POPULARITY_BOOST if is_hot else 0.0)
            )

            raw_attrs = meta.get("attributes")
            attrs = json.loads(raw_attrs) if isinstance(raw_attrs, str) and raw_attrs else raw_attrs

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
                attributes=attrs,
                is_hot=is_hot,
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

    # Dedupe theo product_id — cùng 1 sản phẩm có thể xuất hiện qua nhiều chunk (overview + specs
    # + reviews), giữ lại chunk điểm cao nhất mỗi sản phẩm. Nếu không dedupe ở đây, MMR có thể chọn
    # 2 chunk của CÙNG 1 sản phẩm (embedding overview/specs đủ khác nhau để bị coi là "đa dạng"),
    # khiến số sản phẩm PHÂN BIỆT trả về ít hơn k dù caller (Synth Agent) cần đủ k lựa chọn khác nhau.
    seen_ids: set[str] = set()
    deduped_candidates: list[tuple[ProductDoc, list[float], float]] = []
    for doc, vec, score in raw_candidates:
        if doc.id in seen_ids:
            continue
        seen_ids.add(doc.id)
        deduped_candidates.append((doc, vec, score))

    if price_proximity_target is not None:
        deduped_candidates.sort(key=lambda x: abs(x[0].unit_price - price_proximity_target))
        results_final = [doc for doc, _, _ in deduped_candidates[:k]]
    else:
        top_candidates = [(doc, vec) for doc, vec, _ in deduped_candidates[:TOP_K_INITIAL]]
        results_final = _mmr_select(query_vec, top_candidates, k=k)

    latency = (time.perf_counter() - t0) * 1000
    custom_logger.info(
        f"[HybridSearch] complete | returned={len(results_final)} | {latency:.0f}ms"
    )
    return results_final
