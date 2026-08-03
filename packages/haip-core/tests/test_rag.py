"""测试 RAG 包 — BM25 索引和向量存储."""

from __future__ import annotations

import math
import struct

from haip.rag.bm25 import BM25Index
from haip.rag.pipeline import RAGPipeline
from haip.rag.vector_store import VectorStore


class TestBM25Sanitize:
    def test_simple_query(self):
        result = BM25Index._sanitize_query("股骨颈骨折 老年")
        assert '"股骨颈骨折"' in result
        assert '"老年"' in result

    def test_removes_quotes(self):
        # The sanitizer wraps each word in double-quotes for FTS5 phrase matching
        result = BM25Index._sanitize_query("hello world")
        assert result == '"hello" OR "world"'

    def test_removes_single_quotes(self):
        result = BM25Index._sanitize_query("don't panic")
        assert "'" not in result

    def test_empty_query_returns_empty_string(self):
        result = BM25Index._sanitize_query("")
        assert result == '""'

    def test_truncates_to_10_terms(self):
        words = " ".join(str(i) for i in range(20))
        result = BM25Index._sanitize_query(words)
        # 10 terms max
        terms = [t for t in result.split(" OR ") if t.startswith('"')]
        assert len(terms) <= 10


class TestBM25Index:
    def test_connect_and_ready(self):
        idx = BM25Index(":memory:")
        assert idx.connect() is True
        assert idx.ready is True
        idx.close()

    def test_insert_and_count(self):
        idx = BM25Index(":memory:")
        idx.connect()
        inserted = idx.insert_batch([
            {"id": "g1", "content_type": "guideline", "source_id": "KDIGO_2024",
             "text": "CKD患者Hb<100g/L启动ESA治疗", "metadata": "{}"},
            {"id": "r1", "content_type": "rule", "source_id": "cardio",
             "text": "术前需评估心血管风险", "metadata": "{}"},
        ])
        assert inserted == 2
        assert idx.count() == 2
        idx.close()

    def test_search_finds_results(self):
        idx = BM25Index(":memory:")
        idx.connect()
        idx.insert_batch([
            {"id": "g1", "content_type": "guideline", "source_id": "KDIGO",
             "text": "ESA treatment for CKD patients with Hb less than 100", "metadata": "{}"},
        ])
        results = idx.search("ESA treatment")
        assert len(results) > 0
        assert results[0]["id"] == "g1"
        idx.close()

    def test_search_filters_by_content_type(self):
        idx = BM25Index(":memory:")
        idx.connect()
        idx.insert_batch([
            {"id": "g1", "content_type": "guideline", "source_id": "src",
             "text": "guideline content for test", "metadata": "{}"},
            {"id": "r1", "content_type": "rule", "source_id": "src",
             "text": "rule content for test", "metadata": "{}"},
        ])
        results = idx.search("content", content_type="rule")
        assert len(results) == 1
        assert results[0]["content_type"] == "rule"
        idx.close()

    def test_search_empty_query(self):
        idx = BM25Index(":memory:")
        idx.connect()
        idx.insert_batch([
            {"id": "g1", "content_type": "guideline", "source_id": "KDIGO",
             "text": "test", "metadata": "{}"},
        ])
        assert idx.search("") == []
        idx.close()

    def test_clear_removes_all(self):
        idx = BM25Index(":memory:")
        idx.connect()
        idx.insert_batch([
            {"id": "g1", "content_type": "guideline", "source_id": "src",
             "text": "test", "metadata": "{}"},
        ])
        assert idx.count() == 1
        idx.clear()
        assert idx.count() == 0
        idx.close()

    def test_insert_before_connect_returns_zero(self):
        idx = BM25Index(":memory:")
        assert idx.insert_batch([{"id": "x"}]) == 0
        idx.close()


class TestVectorStorePackUnpack:
    def test_pack_unpack_roundtrip(self):
        vec = [1.0, 2.0, 3.0, 4.0]
        packed = VectorStore._pack_vector(vec)
        unpacked = VectorStore._unpack_vector(packed)
        assert unpacked is not None
        assert len(unpacked) == 4
        assert math.isclose(unpacked[0], 1.0)
        assert math.isclose(unpacked[3], 4.0)

    def test_pack_empty_vector(self):
        packed = VectorStore._pack_vector([])
        assert isinstance(packed, bytes)
        assert len(packed) == 0

    def test_unpack_none(self):
        assert VectorStore._unpack_vector(None) is None

    def test_unpack_empty_bytes(self):
        assert VectorStore._unpack_vector(b"") is None

    def test_unpack_invalid_bytes(self):
        # Odd number of bytes
        assert VectorStore._unpack_vector(b"\x00\x00\x00") is None


class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        sim = VectorStore._cosine_similarity(a, b)
        assert math.isclose(sim, 1.0, rel_tol=1e-5)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        sim = VectorStore._cosine_similarity(a, b)
        assert math.isclose(sim, 0.0, abs_tol=1e-6)

    def test_zero_vector(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        sim = VectorStore._cosine_similarity(a, b)
        assert sim == 0.0

    def test_negative_similarity(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        sim = VectorStore._cosine_similarity(a, b)
        assert math.isclose(sim, -1.0, rel_tol=1e-5)


class TestVectorStore:
    def test_connect_and_ready(self):
        vs = VectorStore(":memory:")
        assert vs.connect() is True
        assert vs.ready is True
        vs.close()

    def test_insert_and_count(self):
        vs = VectorStore(":memory:")
        vs.connect()
        inserted = vs.insert_batch([
            {"id": "v1", "content_type": "guideline", "source_id": "src",
             "text": "test", "embedding": [1.0, 0.5], "metadata": "{}"},
            {"id": "v2", "content_type": "guideline", "source_id": "src2",
             "text": "test2", "embedding": [0.5, 1.0], "metadata": "{}"},
        ])
        assert inserted == 2
        assert vs.count() == 2
        vs.close()

    def test_search_returns_closest(self):
        vs = VectorStore(":memory:")
        vs.connect()
        base_v1 = [1.0, 0.0] + [0.0] * 1022
        base_v2 = [0.0, 1.0] + [0.0] * 1022
        vs.insert_batch([
            {"id": "v1", "content_type": "guideline", "source_id": "src",
             "text": "骨科指南", "embedding": base_v1, "metadata": "{}"},
            {"id": "v2", "content_type": "guideline", "source_id": "src2",
             "text": "心内指南", "embedding": base_v2, "metadata": "{}"},
        ])
        q = [1.0, 0.0] + [0.0] * 1022  # closer to v1
        results = vs.search(q, k=1)
        assert len(results) == 1
        assert results[0]["id"] == "v1"
        vs.close()

    def test_search_empty_store(self):
        vs = VectorStore(":memory:")
        vs.connect()
        results = vs.search([1.0]*1024, k=5)
        assert results == []
        vs.close()

    def test_clear(self):
        vs = VectorStore(":memory:")
        vs.connect()
        vs.insert_batch([
            {"id": "v1", "content_type": "guideline", "source_id": "src",
             "text": "t", "embedding": [1.0], "metadata": "{}"},
        ])
        assert vs.count() == 1
        vs.clear()
        assert vs.count() == 0
        vs.close()

    def test_count_with_content_type_filter(self):
        vs = VectorStore(":memory:")
        vs.connect()
        vs.insert_batch([
            {"id": "g1", "content_type": "guideline", "source_id": "s1",
             "text": "t1", "embedding": [1.0], "metadata": "{}"},
            {"id": "r1", "content_type": "rule", "source_id": "s2",
             "text": "t2", "embedding": [2.0], "metadata": "{}"},
        ])
        assert vs.count("guideline") == 1
        assert vs.count("rule") == 1
        vs.close()

    def test_search_zero_vector_query(self):
        vs = VectorStore(":memory:")
        vs.connect()
        vs.insert_batch([
            {"id": "v1", "content_type": "guideline", "source_id": "src",
             "text": "t", "embedding": [1.0], "metadata": "{}"},
        ])
        results = vs.search([0.0]*1024, k=5)
        assert results == []
        vs.close()


class TestRRFFusion:
    def test_merges_two_sources(self):
        vec = [{"id": "a", "text": "va", "score": 0.9}]
        bm = [{"id": "b", "text": "kb", "score": 0.8}]
        fused = RAGPipeline._rrf_fuse(vec, bm)
        assert len(fused) == 2

    def test_dedup_by_id(self):
        vec = [{"id": "a", "text": "va", "score": 0.9}]
        bm = [{"id": "a", "text": "ka", "score": 0.8}]
        fused = RAGPipeline._rrf_fuse(vec, bm)
        assert len(fused) == 1
        assert fused[0]["id"] == "a"

    def test_higher_ranked_first(self):
        vec = [{"id": "a", "text": "va"}, {"id": "b", "text": "vb"}]
        bm = [{"id": "b", "text": "kb"}, {"id": "a", "text": "ka"}]
        fused = RAGPipeline._rrf_fuse(vec, bm, k=60)
        # id "a" has ranks 0 (vec) and 1 (bm) → higher score
        assert fused[0]["id"] == "a"

    def test_empty_input(self):
        assert RAGPipeline._rrf_fuse([], []) == []
        fused = RAGPipeline._rrf_fuse([], [{"id": "x"}])
        assert len(fused) == 1
        assert fused[0]["id"] == "x"
        fused2 = RAGPipeline._rrf_fuse([{"id": "y"}], [])
        assert len(fused2) == 1
        assert fused2[0]["id"] == "y"


class TestFormatForPrompt:
    def test_formats_results(self):
        pipeline = RAGPipeline.__new__(RAGPipeline)
        results = [{"source_id": "KDIGO", "content_type": "guideline", "text": "ESA treatment guidance"}]
        formatted = pipeline.format_for_prompt(results)
        assert "KDIGO" in formatted
        assert "ESA treatment guidance" in formatted

    def test_empty_results_returns_empty_string(self):
        pipeline = RAGPipeline.__new__(RAGPipeline)
        assert pipeline.format_for_prompt([]) == ""

    def test_uses_chinese_labels(self):
        pipeline = RAGPipeline.__new__(RAGPipeline)
        results = [{"source_id": "cardio", "content_type": "rule", "text": "anti-coag rule"}]
        formatted = pipeline.format_for_prompt(results)
        assert "规则" in formatted
