"""RAG pipeline — RRF hybrid search + result formatting.

Combines VectorStore (semantic) and BM25Index (keyword) via Reciprocal Rank Fusion.
Formats retrieved results for injection into LLM system prompt.
"""

from __future__ import annotations

import logging

from haip.rag.bm25 import BM25Index
from haip.rag.embedding import EmbeddingProvider
from haip.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Hybrid search pipeline: Vector (semantic) + BM25 (keyword) → RRF fusion → format.

    Designed as a per-request ephemeral or singleton-scoped pipeline.
    """

    _index_ready = False

    def __init__(self, vector_store: VectorStore, bm25: BM25Index):
        self._vs = vector_store
        self._bm = bm25

    @classmethod
    def ready(cls) -> bool:
        return cls._index_ready

    @classmethod
    def mark_ready(cls):
        cls._index_ready = True

    @classmethod
    def mark_not_ready(cls):
        cls._index_ready = False

    def search(self, query: str, top_k: int = 5, content_type: str | None = None) -> list[dict]:
        """Hybrid search: vector + BM25 → RRF fusion → top-k results."""
        if not self._vs.ready or not self._bm.ready:
            return []

        ep = EmbeddingProvider
        query_vec = ep.encode_single(query)

        vec_results = self._vs.search(query_vec, content_type=content_type, k=top_k * 2)
        bm_results = self._bm.search(query, content_type=content_type, k=top_k * 2)

        fused = self._rrf_fuse(vec_results, bm_results, k=60)
        return fused[:top_k]

    def format_for_prompt(self, results: list[dict], max_tokens: int = 1000) -> str:
        """Format search results as a string for LLM system prompt injection."""
        if not results:
            return ""

        lines = ["[检索到的相关知识]"]
        char_budget = max_tokens * 3  # rough char estimate
        used = 0

        for i, r in enumerate(results):
            source = r.get("source_id", "?")
            ctype = r.get("content_type", "")
            text = r.get("text", "")
            type_label = {"guideline": "指南", "rule": "规则", "patient": "相似病例"}.get(ctype, ctype)

            line = f"\n[{i + 1}] [{type_label}] {source}: {text[:300]}"
            if used + len(line) > char_budget:
                break
            lines.append(line)
            used += len(line)

        if len(results) > len(lines) - 1:
            lines.append(f"\n... 共 {len(results)} 条结果，已截断")

        return "".join(lines)

    @staticmethod
    def _rrf_fuse(vec_results: list[dict], bm_results: list[dict], k: int = 60) -> list[dict]:
        """Reciprocal Rank Fusion: merge and dedup vector + BM25 results."""
        scores: dict[str, float] = {}
        items: dict[str, dict] = {}

        for rank, item in enumerate(vec_results):
            rid = item["id"]
            scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank + 1)
            if rid not in items:
                items[rid] = dict(item)
            items[rid]["score"] = round(scores[rid], 4)

        for rank, item in enumerate(bm_results):
            rid = item["id"]
            scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank + 1)
            if rid not in items:
                items[rid] = dict(item)
            items[rid]["score"] = round(scores[rid], 4)

        return sorted(items.values(), key=lambda x: x["score"], reverse=True)
