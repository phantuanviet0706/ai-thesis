from langchain_openai import OpenAIEmbeddings

from common.constants import EMBEDDING_MODEL, EMBEDDING_DIMS
from core.config import settings

_embedding_model: OpenAIEmbeddings | None = None


def get_embedding_model() -> OpenAIEmbeddings:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            dimensions=EMBEDDING_DIMS,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    return _embedding_model


def embed_query(text: str) -> list[float]:
    return get_embedding_model().embed_query(text)


def embed_documents(texts: list[str]) -> list[list[float]]:
    return get_embedding_model().embed_documents(texts)
