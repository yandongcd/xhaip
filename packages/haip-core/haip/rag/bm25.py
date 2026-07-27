"""BM25 keyword index — SQLite FTS5-backed full-text search.

Provides keyword-based retrieval as the second prong of RRF hybrid search.
Reuses the existing SQLite FTS5 infrastructure already in use by KnowledgeStore.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


class BM25Index:
    """SQLite FTS5 full-text search for keyword matching.

    Complementary to vector search — excels at exact term matching
    (e.g., "Garden III", "Caprini 评分") where semantic search may miss.
    """

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    def connect(self) -> bool:
        """Open connection and create FTS5 table."""
        try:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS rag_fts USING fts5(
                    id, content_type, source_id, text, metadata,
                    tokenize='unicode61 remove_diacritics 0'
                )
            """)
            self._ready = True
        except Exception as e:
            logger.warning("BM25 FTS5 init failed: %s", e)
            self._ready = False
        return self._ready

    def insert_batch(self, rows: list[dict]) -> int:
        if not self._ready or not self._conn:
            return 0
        count = 0
        for row in rows:
            try:
                self._conn.execute(
                    "INSERT OR REPLACE INTO rag_fts(id, content_type, source_id, text, metadata) VALUES(?,?,?,?,?)",
                    (row["id"], row["content_type"], row["source_id"],
                     row.get("text", ""), row.get("metadata", "{}")),
                )
                count += 1
            except Exception as e:
                logger.error("FTS5 insert failed for %s: %s", row.get("id", "?"), e)
        self._conn.commit()
        return count

    def search(self, query: str, content_type: str | None = None, k: int = 10) -> list[dict]:
        """FTS5 search with BM25 ranking. Returns scored results."""
        if not self._ready or not self._conn or not query.strip():
            return []

        safe_query = self._sanitize_query(query)
        where = "WHERE rag_fts MATCH ? AND content_type = ?" if content_type else "WHERE rag_fts MATCH ?"
        params = (safe_query, content_type) if content_type else (safe_query,)

        try:
            rows = self._conn.execute(
                f"SELECT id, content_type, source_id, text, metadata, rank FROM rag_fts {where} ORDER BY rank LIMIT ?",
                (*params, k),
            ).fetchall()
        except Exception:
            return []

        return [
            {
                "id": r[0], "content_type": r[1], "source_id": r[2],
                "text": r[3], "metadata": r[4], "score": round(1.0 / (abs(r[5]) + 1), 4),
            }
            for r in rows
        ]

    def count(self) -> int:
        if not self._conn:
            return 0
        row = self._conn.execute("SELECT COUNT(*) FROM rag_fts").fetchone()
        return row[0] if row else 0

    def clear(self):
        if self._conn:
            self._conn.execute("DELETE FROM rag_fts")
            self._conn.commit()

    @staticmethod
    def _sanitize_query(query: str) -> str:
        cleaned = query.replace('"', ' ').replace("'", " ")
        parts = [p for p in cleaned.split() if p]
        if not parts:
            return '""'
        return " OR ".join(f'"{p}"' for p in parts[:10])

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            self._ready = False
