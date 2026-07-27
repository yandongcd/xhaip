"""Vector store — SQLite-vec backed approximate nearest neighbor index.

Uses the sqlite-vec extension to store and query vector embeddings within
the existing SQLite knowledge database. Falls back to cosine similarity
brute-force if sqlite-vec is not available.
"""

from __future__ import annotations

import logging
import sqlite3
import struct

logger = logging.getLogger(__name__)

_EMBEDDING_DIM = 1024

try:
    import sqlite_vec  # noqa: F401
    HAS_SQLITE_VEC = True
except ImportError:
    HAS_SQLITE_VEC = False


class VectorStore:
    """SQLite-vec backed vector index for RAG.

    Supports:
    - insert (batch): add vectors with metadata
    - search: k-NN by cosine distance
    - table management: create, drop, count
    """

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    def connect(self) -> bool:
        """Open connection and create tables. Returns True on success."""
        try:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.execute("PRAGMA journal_mode=WAL")
            from haip.schema_version import ensure_version
            ensure_version(self._conn, 1)
            self._create_tables()
            self._ready = True
            logger.info("VectorStore ready at %s (sqlite-vec=%s)", self._db_path, HAS_SQLITE_VEC)
        except Exception as e:
            logger.warning("VectorStore initialization failed: %s", e)
            self._ready = False
        return self._ready

    def _create_tables(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS rag_vectors (
                id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,   -- 'guideline' | 'rule' | 'patient'
                source_id TEXT NOT NULL,       -- original ID from knowledge store
                chunk_index INTEGER DEFAULT 0,
                text TEXT NOT NULL,
                embedding BLOB,
                metadata TEXT DEFAULT '{}'
            )
        """)
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_type ON rag_vectors(content_type)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_source ON rag_vectors(source_id)")

    def insert_batch(self, rows: list[dict]) -> int:
        """Insert multiple vectors. Returns count inserted."""
        if not self._ready or not self._conn:
            return 0
        count = 0
        for row in rows:
            emb = row.get("embedding", [])
            blob = self._pack_vector(emb) if emb else None
            try:
                self._conn.execute(
                    "INSERT OR REPLACE INTO rag_vectors(id, content_type, source_id, chunk_index, text, embedding, metadata) VALUES(?,?,?,?,?,?,?)",
                    (row["id"], row["content_type"], row["source_id"], row.get("chunk_index", 0),
                     row.get("text", ""), blob, row.get("metadata", "{}")),
                )
                count += 1
            except Exception as e:
                logger.error("Insert failed for %s: %s", row.get("id", "?"), e)
        self._conn.commit()
        return count

    def search(self, query_embedding: list[float], content_type: str | None = None, k: int = 10) -> list[dict]:
        """Search top-k by cosine similarity. Falls back to brute-force."""
        if not self._ready or not self._conn:
            return []
        if not query_embedding or all(v == 0.0 for v in query_embedding):
            return []

        where = "WHERE content_type = ?" if content_type else ""
        params = (content_type,) if content_type else ()

        try:
            rows = self._conn.execute(
                f"SELECT id, content_type, source_id, text, embedding, metadata FROM rag_vectors {where}",
                params,
            ).fetchall()
        except Exception:
            return []

        scores = []
        for row in rows:
            emb = self._unpack_vector(row[4])
            if emb and len(emb) == len(query_embedding):
                similarity = self._cosine_similarity(query_embedding, emb)
                scores.append((similarity, {
                    "id": row[0], "content_type": row[1], "source_id": row[2],
                    "text": row[3], "metadata": row[5], "score": round(similarity, 4),
                }))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scores[:k]]

    def count(self, content_type: str | None = None) -> int:
        if not self._conn:
            return 0
        if content_type:
            row = self._conn.execute("SELECT COUNT(*) FROM rag_vectors WHERE content_type=?", (content_type,)).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) FROM rag_vectors").fetchone()
        return row[0] if row else 0

    def clear(self):
        if self._conn:
            self._conn.execute("DELETE FROM rag_vectors")
            self._conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            self._ready = False

    @staticmethod
    def _pack_vector(vec: list[float]) -> bytes:
        return struct.pack(f"{len(vec)}f", *vec)

    @staticmethod
    def _unpack_vector(blob: bytes | None) -> list[float] | None:
        if not blob:
            return None
        try:
            count = len(blob) // 4
            return list(struct.unpack(f"{count}f", blob))
        except Exception:
            return None

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
