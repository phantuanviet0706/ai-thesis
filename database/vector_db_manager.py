import chromadb
from chromadb import Collection

from common.constants import (
    COLLECTION_OVERVIEW,
    COLLECTION_SPECS,
    COLLECTION_REVIEWS,
)
from core.config import settings

_COLLECTION_METADATA = {"hnsw:space": "cosine", "hnsw:M": 16, "hnsw:ef_construction": 200}


class VectorDBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        return cls._instance

    def get_collection(self, name: str) -> Collection:
        return self.client.get_or_create_collection(name=name, metadata=_COLLECTION_METADATA)

    def get_all_collections(self) -> dict[str, Collection]:
        return {
            COLLECTION_OVERVIEW: self.get_collection(COLLECTION_OVERVIEW),
            COLLECTION_SPECS: self.get_collection(COLLECTION_SPECS),
            COLLECTION_REVIEWS: self.get_collection(COLLECTION_REVIEWS),
        }

    def upsert_documents(
        self,
        collection_name: str,
        ids: list,
        documents: list,
        metadatas: list = None,
        embeddings: list = None,
    ):
        vecs = embeddings or self._embed(documents)
        self.get_collection(collection_name).upsert(
            ids=ids, documents=documents, embeddings=vecs, metadatas=metadatas
        )

    def add_documents(
        self,
        collection_name: str,
        ids: list,
        documents: list,
        metadatas: list = None,
        embeddings: list = None,
    ):
        vecs = embeddings or self._embed(documents)
        self.get_collection(collection_name).add(
            ids=ids, documents=documents, embeddings=vecs, metadatas=metadatas
        )

    def update_documents(
        self,
        collection_name: str,
        ids: list,
        documents: list,
        metadatas: list = None,
        embeddings: list = None,
    ):
        vecs = embeddings or self._embed(documents)
        self.get_collection(collection_name).update(
            ids=ids, documents=documents, embeddings=vecs, metadatas=metadatas
        )

    def delete_documents(
        self,
        collection_name: str,
        ids: list = None,
        filter_metadatas: dict = None,
    ):
        self.get_collection(collection_name).delete(ids=ids, where=filter_metadatas)

    def query_similarity(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        filter_metadata: dict = None,
    ):
        from retrieval.embeddings import embed_query
        query_vec = embed_query(query_text)
        return self.get_collection(collection_name).query(
            query_embeddings=[query_vec],
            n_results=n_results,
            where=filter_metadata,
        )

    def count(self, collection_name: str) -> int:
        return self.get_collection(collection_name).count()

    @staticmethod
    def _embed(documents: list) -> list:
        from retrieval.embeddings import embed_documents
        return embed_documents(documents)
