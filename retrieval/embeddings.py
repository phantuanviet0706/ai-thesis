from langchain_openai import OpenAIEmbeddings

from constants.constants import EMBEDDING_MODEL, EMBEDDING_DIMS
from core.logger import custom_logger

_embedding_model: OpenAIEmbeddings | None = None


def get_embedding_model() -> OpenAIEmbeddings | None:
    """
    @desc Khởi tạo và trả về model embedding theo cơ chế singleton — chỉ tạo một lần duy nhất
    @return OpenAIEmbeddings | None: Đối tượng model embedding đang hoạt động
    """
    global _embedding_model
    if _embedding_model is None:
        custom_logger.info(
            f"[Embeddings] Initializing model={EMBEDDING_MODEL} dims={EMBEDDING_DIMS}"
        )
        _embedding_model = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            dimensions=EMBEDDING_DIMS,
        )
        custom_logger.info("[Embeddings] Model ready")
    return _embedding_model


def embed_query(text: str) -> list[float]:
    """
    @desc Chuyển đổi một chuỗi truy vấn thành vector embedding
    @params text (str): Chuỗi văn bản cần embedding
    @return list[float]: Danh sách các giá trị float biểu diễn vector embedding
    """
    return get_embedding_model().embed_query(text)


def embed_documents(texts: list[str]) -> list[list[float]]:
    """
    @desc Chuyển đổi danh sách các văn bản thành danh sách vector embedding tương ứng
    @params texts (list[str]): Danh sách các chuỗi văn bản cần embedding
    @return list[list[float]]: Danh sách các vector embedding tương ứng với từng văn bản
    """
    custom_logger.debug(f"[Embeddings] embed_documents | count={len(texts)}")
    return get_embedding_model().embed_documents(texts)
