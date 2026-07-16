"""Fixed Top-5 semantic retrieval orchestration for Day 7."""

from functools import lru_cache

from backend.app.services.embedding import EmbeddingClient, get_embedding_client
from backend.app.services.qdrant_store import (
    QdrantVectorStore,
    RetrievedChunk,
    get_qdrant_vector_store,
)

RETRIEVAL_TOP_K = 5


class RetrievalService:
    """Encode one query and retrieve a fixed number of Qdrant payloads."""

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        vector_store: QdrantVectorStore,
    ) -> None:
        self._embedding_client = embedding_client
        self._vector_store = vector_store

    def search(self, query: str) -> list[RetrievedChunk]:
        """Return at most five semantically similar Chunks."""
        query_vector = self._embedding_client.embed_query(query)
        return self._vector_store.search(query_vector, limit=RETRIEVAL_TOP_K)


@lru_cache
def get_retrieval_service() -> RetrievalService:
    """Return the lazy process-wide retrieval service."""
    return RetrievalService(get_embedding_client(), get_qdrant_vector_store())
