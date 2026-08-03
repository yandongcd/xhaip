"""Index builder — constructs RAG vector + BM25 indices from YAML knowledge + patient JSON.

Runs at startup (or on-demand rebuild). Reads:
- Guidelines from knowledge/guidelines/ (YAML, by section)
- Rules from knowledge/rules/ (YAML, atomic)
- Patients from patients.json (structured clinical summary)
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import yaml

from haip.rag.bm25 import BM25Index
from haip.rag.embedding import EmbeddingProvider
from haip.rag.pipeline import RAGPipeline
from haip.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class IndexBuilder:
    """Builds vector and BM25 indices from xhaip knowledge base and patient data."""

    def __init__(self, vector_store: VectorStore, bm25: BM25Index, knowledge_dir: str, patients_file: str):
        self._vs = vector_store
        self._bm = bm25
        self._knowledge_dir = Path(knowledge_dir)
        self._patients_file = Path(patients_file)
        self._last_build_time: float = 0

    @property
    def age_seconds(self) -> float:
        return time.time() - self._last_build_time if self._last_build_time else float("inf")

    def build(self) -> int:
        """Full index build. Returns total rows indexed."""
        ep = EmbeddingProvider
        if not ep.ready():
            ep.load()
        if not ep.ready():
            logger.warning("Embedding not available, building BM25-only index")
            return self._build_bm25_only()

        all_rows = []
        all_rows.extend(self._index_guidelines())
        all_rows.extend(self._index_rules())
        all_rows.extend(self._index_patients())

        if not all_rows:
            return 0

        self._embed_and_insert(all_rows)
        self._last_build_time = time.time()
        RAGPipeline.mark_ready()
        logger.info("Index built: %d rows in %.1fs", len(all_rows), time.time() - self._last_build_time)
        return len(all_rows)

    def needs_rebuild(self, patients_mtime: float) -> bool:
        """Check if patients.json has been modified since last build."""
        return patients_mtime > self._last_build_time

    def _embed_and_insert(self, rows: list[dict]):
        """Batch embed texts and insert into both indices."""
        texts = [r["text"] for r in rows]
        embeddings = EmbeddingProvider.encode(texts)
        for row, emb in zip(rows, embeddings):
            row["embedding"] = emb
        self._vs.insert_batch(rows)
        self._bm.insert_batch(rows)

    def _build_bm25_only(self) -> int:
        all_rows = []
        all_rows.extend(self._index_guidelines())
        all_rows.extend(self._index_rules())
        all_rows.extend(self._index_patients())
        if all_rows:
            self._bm.insert_batch(all_rows)
            self._last_build_time = time.time()
            RAGPipeline.mark_ready()
        return len(all_rows)

    def _index_guidelines(self) -> list[dict]:
        rows = []
        guidelines_dir = self._knowledge_dir / "guidelines"
        if not guidelines_dir.is_dir():
            return rows
        for yf in guidelines_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
                if not isinstance(data, dict):
                    continue
                guideline_name = data.get("name", yf.stem)
                trust = data.get("trust_level", "T2")
                publisher = data.get("publisher", "")
                sections = data.get("sections", [])
                if not sections:
                    text = data.get("content") or data.get("description") or ""
                    if text.strip():
                        rows.append(self._make_row(guideline_name, "guideline", guideline_name, 0, text, {
                            "name": guideline_name, "trust_level": trust, "publisher": publisher,
                        }))
                else:
                    for i, section in enumerate(sections):
                        sec_text = section if isinstance(section, str) else section.get("content", "")
                        sec_title = section.get("title", f"§{i + 1}") if isinstance(section, dict) else f"§{i + 1}"
                        if sec_text.strip():
                            chunk_text = f"{guideline_name} — {sec_title}: {sec_text}"
                            rows.append(self._make_row(
                                f"{guideline_name}#{i}", "guideline", guideline_name, i, chunk_text,
                                {"name": guideline_name, "section": sec_title, "trust_level": trust, "publisher": publisher},
                            ))
            except Exception as e:
                logger.warning("Skipping guideline %s: %s", yf.name, e)
        logger.info("Indexed %d guideline chunks", len(rows))
        return rows

    def _index_rules(self) -> list[dict]:
        rows = []
        rules_dir = self._knowledge_dir / "rules"
        if not rules_dir.is_dir():
            return rows
        for yf in rules_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
                rules = data.get("rules", [])
                rule_set = data.get("name", yf.stem)
                for i, rule in enumerate(rules):
                    if not isinstance(rule, dict):
                        continue
                    dp = rule.get("decision_point", "")
                    conclusion = rule.get("conclusion", "")
                    rule_text = f"{rule_set}: {dp} → {conclusion}"
                    rows.append(self._make_row(
                        f"{rule_set}#{i}", "rule", rule_set, i, rule_text,
                        {"rule_set": rule_set, "decision_point": dp, "priority": rule.get("priority", "medium")},
                    ))
            except Exception as e:
                logger.warning("Skipping rule file %s: %s", yf.name, e)
        logger.info("Indexed %d rules", len(rows))
        return rows

    def _index_patients(self) -> list[dict]:
        rows = []
        if not self._patients_file.exists():
            logger.warning("Patients file not found: %s", self._patients_file)
            return rows
        try:
            data = json.loads(self._patients_file.read_text(encoding="utf-8"))
            patients = data.get("patients", []) if isinstance(data, dict) else data
        except Exception as e:
            logger.warning("Failed to load patients: %s", e)
            return rows

        for p in patients:
            if not isinstance(p, dict):
                continue
            pid = p.get("patient_id", p.get("id", "?"))
            summary = self._patient_summary(p)
            rows.append(self._make_row(
                f"pt_{pid}", "patient", str(pid), 0, summary,
                {"patient_id": str(pid), "department": p.get("department", ""), "diagnosis": p.get("diagnosis", "")},
            ))
        logger.info("Indexed %d patient summaries", len(rows))
        return rows

    @staticmethod
    def _patient_summary(p: dict) -> str:
        """Build structured clinical summary for embedding."""
        gender = p.get("gender", "")
        age = p.get("age", p.get("age_years", ""))
        diagnosis = p.get("diagnosis", "")
        dept = p.get("department", "")
        urgency = p.get("urgency", "")

        labs = p.get("lab_results", {})
        lab_parts = []
        for k, v in labs.items():
            if isinstance(v, (int, float)):
                lab_parts.append(f"{k}={v}")

        return (
            f"性别:{gender}, 年龄:{age}, 科室:{dept}, 诊断:{diagnosis}, "
            f"紧急度:{urgency}, 检验:{' '.join(lab_parts[:8])}"
        )

    @staticmethod
    def _make_row(rid: str, content_type: str, source_id: str, chunk_idx: int, text: str, meta: dict) -> dict:
        """Create a normalized insert row."""
        return {
            "id": f"{content_type}:{rid}",
            "content_type": content_type,
            "source_id": source_id,
            "chunk_index": chunk_idx,
            "text": text,
            "metadata": json.dumps(meta, ensure_ascii=False),
        }
