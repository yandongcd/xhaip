"""RAG (Retrieval-Augmented Generation) — semantic + keyword hybrid search.

Phase 1 of xhaip intelligence upgrade.
Provides: EmbeddingProvider (BGE-M3), VectorStore (SQLite-vec), BM25 (FTS5),
RRF hybrid search pipeline, and index builder.
"""

from haip.rag.bm25 import BM25Index
from haip.rag.embedding import EmbeddingProvider, get_embedding_provider
from haip.rag.index_builder import IndexBuilder
from haip.rag.pipeline import RAGPipeline
from haip.rag.vector_store import VectorStore

__all__ = [
    "BM25Index",
    "EmbeddingProvider",
    "IndexBuilder",
    "RAGPipeline",
    "VectorStore",
    "get_embedding_provider",
]
