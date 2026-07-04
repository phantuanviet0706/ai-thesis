from sentence_transformers import SentenceTransformer

from constants.constants import EMBEDDING_MODEL, EMBEDDING_DIMS
from core.logger import custom_logger

_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """
    @desc Khởi tạo và trả về local embedding model theo cơ chế singleton
    @return SentenceTransformer: Model đang hoạt động
    """
    global _embedding_model
    if _embedding_model is None:
        custom_logger.info(
            f"[Embeddings] Loading local model={EMBEDDING_MODEL} dims={EMBEDDING_DIMS}"
        )
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        custom_logger.info("[Embeddings] Model ready")
    return _embedding_model


def embed_query(text: str) -> list[float]:
    """
    @desc Chuyển đổi một chuỗi truy vấn thành vector embedding
    @params text (str): Chuỗi văn bản cần embedding
    @return list[float]: Vector embedding đã chuẩn hóa L2
    """
    return get_embedding_model().encode(text, normalize_embeddings=True).tolist()


def embed_documents(texts: list[str]) -> list[list[float]]:
    """
    @desc Chuyển đổi danh sách văn bản thành danh sách vector embedding
    @params texts (list[str]): Danh sách văn bản cần embedding
    @return list[list[float]]: Danh sách vector embedding tương ứng
    """
    custom_logger.debug(f"[Embeddings] embed_documents | count={len(texts)}")
    return get_embedding_model().encode(texts, normalize_embeddings=True).tolist()
