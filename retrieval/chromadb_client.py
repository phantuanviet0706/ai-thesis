import chromadb
from chromadb import Collection

from common.constants import (
    COLLECTION_OVERVIEW,
    COLLECTION_SPECS,
    COLLECTION_REVIEWS,
)
from core.config import settings

_client: chromadb.ClientAPI | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
    return _client


def _get_or_create_collection(name: str, metadata: dict) -> Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata=metadata,
    )


def get_overview_collection() -> Collection:
    """USP + short descriptions — 256 tokens, 32 overlap. Used for general queries."""
    return _get_or_create_collection(
        COLLECTION_OVERVIEW,
        {"hnsw:space": "cosine", "hnsw:M": 16, "hnsw:ef_construction": 200},
    )


def get_specs_collection() -> Collection:
    """Detailed technical specs — 512 tokens, 64 overlap. Used for technical queries."""
    return _get_or_create_collection(
        COLLECTION_SPECS,
        {"hnsw:space": "cosine", "hnsw:M": 16, "hnsw:ef_construction": 200},
    )


def get_reviews_collection() -> Collection:
    """Reviews + social proof — 384 tokens, 48 overlap. Used for trust/experience queries."""
    return _get_or_create_collection(
        COLLECTION_REVIEWS,
        {"hnsw:space": "cosine", "hnsw:M": 16, "hnsw:ef_construction": 200},
    )


def get_all_collections() -> dict[str, Collection]:
    return {
        COLLECTION_OVERVIEW: get_overview_collection(),
        COLLECTION_SPECS: get_specs_collection(),
        COLLECTION_REVIEWS: get_reviews_collection(),
    }
