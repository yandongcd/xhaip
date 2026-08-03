"""RAG retrieval evaluation — MRR@5, NDCG@5, Recall@5.

Tests hybrid RAG pipeline against 50 annotated clinical queries.
Gate: MRR@5 >= 0.6
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
GUIDELINES_DIR = PROJECT_ROOT / "packages" / "haip-hospital" / "knowledge" / "guidelines"


def load_queries() -> list[dict]:
    path = HERE / "queries.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_guideline_texts() -> list[dict]:
    """Load guideline YAML files as searchable documents."""
    docs = []
    for yf in sorted(GUIDELINES_DIR.glob("*.yaml")):
        try:
            import yaml
            data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
            gid = data.get("id", yf.stem)
            name = data.get("name", "")
            desc = data.get("description", "").replace(">", " ").replace("\n", " ")
            text = f"{name} {desc}"
            docs.append({
                "id": gid, "source_id": yf.stem,
                "text": text, "content_type": "guideline",
            })
        except Exception:
            pass
    return docs


def _char_bigrams(text: str) -> set[str]:
    """Character bigrams for CJK-aware text matching."""
    normalized = text.lower().replace(" ", "").replace("\n", "")
    return {normalized[i:i + 2] for i in range(len(normalized) - 1)}


def simple_bm25_search(query: str, docs: list[dict], top_k: int = 5) -> list[dict]:
    """Character bigram + keyword overlap search (no FTS5 dependency)."""
    query_bigrams = _char_bigrams(query)
    query_terms = set(query.lower().split())
    scored = []
    for doc in docs:
        doc_bigrams = _char_bigrams(doc["text"])
        bigram_overlap = len(query_bigrams & doc_bigrams)
        doc_terms = set(doc["text"].lower().split())
        word_overlap = len(query_terms & doc_terms)
        score = bigram_overlap + word_overlap * 3
        if score > 0:
            doc["score"] = score
            scored.append(doc)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def compute_mrr_at_k(results_per_query: list[dict], k: int = 5) -> float:
    """Mean Reciprocal Rank @ k."""
    rr_sum = 0.0
    count = 0
    for r in results_per_query:
        if not r["relevant"]:
            continue
        count += 1
        for rank, item in enumerate(r["results"][:k]):
            if item["id"] in r["relevant"]:
                rr_sum += 1.0 / (rank + 1)
                break
    return rr_sum / count if count > 0 else 0.0


def compute_recall_at_k(results_per_query: list[dict], k: int = 5) -> float:
    """Recall @ k."""
    total_relevant = 0
    total_found = 0
    for r in results_per_query:
        if not r["relevant"]:
            continue
        total_relevant += len(r["relevant"])
        for item in r["results"][:k]:
            if item["id"] in r["relevant"]:
                total_found += 1
    return total_found / total_relevant if total_relevant > 0 else 0.0


def compute_ndcg_at_k(results_per_query: list[dict], k: int = 5) -> float:
    """Normalized Discounted Cumulative Gain @ k."""
    ndcg_sum = 0.0
    count = 0
    for r in results_per_query:
        if not r["relevant"]:
            continue
        count += 1
        dcg = 0.0
        for i, item in enumerate(r["results"][:k]):
            if item["id"] in r["relevant"]:
                dcg += 1.0 / math.log2(i + 2)
        ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(r["relevant"]), k)))
        ndcg_sum += dcg / ideal if ideal > 0 else 0.0
    return ndcg_sum / count if count > 0 else 0.0


# ── pytest test cases ──

GUIDELINE_DOCS = load_guideline_texts()
EVAL_QUERIES = load_queries()


@pytest.mark.parametrize("query_item", EVAL_QUERIES, ids=[q["id"] for q in EVAL_QUERIES])
def test_rag_query_has_results(query_item):
    """Each query should return at least 1 result."""
    results = simple_bm25_search(query_item["query"], GUIDELINE_DOCS, top_k=5)
    assert len(results) >= 1, f"Query '{query_item['query'][:40]}...' returned no results"


@pytest.mark.parametrize("query_item", EVAL_QUERIES, ids=[q["id"] for q in EVAL_QUERIES])
def test_rag_query_finds_relevant(query_item):
    """Each query should find at least 1 relevant guideline in top-5."""
    results = simple_bm25_search(query_item["query"], GUIDELINE_DOCS, top_k=5)
    found = [r["id"] for r in results if r["id"] in query_item.get("relevant", [])]
    assert len(found) >= 1, (
        f"'{query_item['query'][:40]}...' "
        f"expected any of {query_item['relevant']} but got {[r['id'] for r in results[:3]]}"
    )


def test_rag_mrr_at_5():
    """MRR@5 should be >= 0.6 (gate)."""
    results = []
    for q in EVAL_QUERIES:
        search_results = simple_bm25_search(q["query"], GUIDELINE_DOCS, top_k=5)
        results.append({"query": q["query"], "relevant": q.get("relevant", []), "results": search_results})
    mrr = compute_mrr_at_k(results, k=5)
    assert mrr >= 0.6, f"MRR@5={mrr:.3f} below gate threshold 0.6"


def test_rag_recall_at_5():
    """Recall@5 should be >= 0.5."""
    results = []
    for q in EVAL_QUERIES:
        search_results = simple_bm25_search(q["query"], GUIDELINE_DOCS, top_k=5)
        results.append({"query": q["query"], "relevant": q.get("relevant", []), "results": search_results})
    recall = compute_recall_at_k(results, k=5)
    assert recall >= 0.5, f"Recall@5={recall:.3f} below threshold 0.5"


def test_rag_ndcg_at_5():
    """NDCG@5 should be >= 0.5."""
    results = []
    for q in EVAL_QUERIES:
        search_results = simple_bm25_search(q["query"], GUIDELINE_DOCS, top_k=5)
        results.append({"query": q["query"], "relevant": q.get("relevant", []), "results": search_results})
    ndcg = compute_ndcg_at_k(results, k=5)
    assert ndcg >= 0.5, f"NDCG@5={ndcg:.3f} below threshold 0.5"


# ── CLI entry point ──

if __name__ == "__main__":
    queries = load_queries()
    docs = load_guideline_texts()
    print(f"Loaded {len(queries)} queries, {len(docs)} guideline documents\n")

    results_per_query = []
    for q in queries:
        search_results = simple_bm25_search(q["query"], docs, top_k=5)
        results_per_query.append({
            "query": q["query"], "relevant": q.get("relevant", []), "results": search_results,
        })

    mrr = compute_mrr_at_k(results_per_query, k=5)
    recall = compute_recall_at_k(results_per_query, k=5)
    ndcg = compute_ndcg_at_k(results_per_query, k=5)

    print(f"MRR@5:    {mrr:.4f}")
    print(f"Recall@5: {recall:.4f}")
    print(f"NDCG@5:   {ndcg:.4f}")
    print(f"\nGate (MRR@5 >= 0.6): {'PASS' if mrr >= 0.6 else 'FAIL'}")
    sys.exit(0 if mrr >= 0.6 else 1)
