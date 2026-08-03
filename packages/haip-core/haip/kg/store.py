"""KG 存储层 — SQLite 实体表 + VectorStore 语义索引 (复用 haip.rag)."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

_DEFAULT_DB = Path(__file__).resolve().parent.parent.parent.parent / "xhaip_memory.db"

ENTITY_TABLES = {
    "kg_guidelines": """
        CREATE TABLE IF NOT EXISTS kg_guidelines (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            abbr TEXT,
            publisher TEXT,
            trust_level TEXT,
            version TEXT,
            description TEXT,
            source_file TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """,
    "kg_rules": """
        CREATE TABLE IF NOT EXISTS kg_rules (
            id TEXT PRIMARY KEY,
            rule_set_id TEXT NOT NULL,
            decision_point TEXT,
            condition_expr TEXT,
            conclusion TEXT,
            certainty TEXT,
            evidence_sources TEXT,
            source_file TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """,
    "kg_bp_steps": """
        CREATE TABLE IF NOT EXISTS kg_bp_steps (
            id TEXT PRIMARY KEY,
            bp_id TEXT NOT NULL,
            name TEXT NOT NULL,
            actor TEXT,
            description TEXT,
            decision TEXT,
            data_used TEXT,
            rule_ids TEXT,
            source_file TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """,
    "kg_departments": """
        CREATE TABLE IF NOT EXISTS kg_departments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            source_file TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """,
    "kg_diagnoses": """
        CREATE TABLE IF NOT EXISTS kg_diagnoses (
            icd10 TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            compatible_agents TEXT,
            source_file TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """,
}

RELATION_TABLES = {
    "kg_relations": """
        CREATE TABLE IF NOT EXISTS kg_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            trust_level TEXT,
            evidence TEXT,
            created_at REAL NOT NULL
        )
    """,
}


class KGStore:
    """知识图谱存储: 实体表 + 关系表 + 向量索引."""

    def __init__(self, db_path: str = ""):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self._init()

    def _init(self) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute("PRAGMA journal_mode=WAL")
            for ddl in ENTITY_TABLES.values():
                conn.execute(ddl)
            for ddl in RELATION_TABLES.values():
                conn.execute(ddl)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kr_source ON kg_relations(source_type, source_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kr_target ON kg_relations(target_type, target_id)")
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    # ── 实体写入 ──

    def upsert_guideline(self, **fields: Any) -> None:
        gid = fields.get("id", "")
        if not gid:
            return
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO kg_guidelines (id, name, abbr, publisher, trust_level, version, description, source_file, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (gid, fields["name"], fields.get("abbr"), fields.get("publisher"),
                 fields.get("trust_level"), fields.get("version"), fields.get("description", ""),
                 fields["source_file"], __import__("time").time()),
            )
            conn.commit()

    def upsert_rule(self, **fields: Any) -> None:
        rid = fields.get("id", "")
        if not rid:
            return
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO kg_rules (id, rule_set_id, decision_point, condition_expr, conclusion, certainty, evidence_sources, source_file, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (rid, fields["rule_set_id"], fields.get("decision_point"), fields.get("condition_expr"),
                 fields.get("conclusion"), fields.get("certainty"),
                 json.dumps(fields.get("evidence_sources", [])),
                 fields["source_file"], __import__("time").time()),
            )
            conn.commit()

    def upsert_bp_step(self, sid: str, **fields: Any) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO kg_bp_steps (id, bp_id, name, actor, description, decision, data_used, rule_ids, source_file, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (sid, fields["bp_id"], fields["name"], fields.get("actor"),
                 fields.get("description"), fields.get("decision"),
                 json.dumps(fields.get("data_used", [])),
                 json.dumps(fields.get("rule_ids", [])),
                 fields["source_file"], __import__("time").time()),
            )
            conn.commit()

    def upsert_department(self, did: str, **fields: Any) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO kg_departments (id, name, type, source_file, created_at) VALUES (?,?,?,?,?)",
                (did, fields["name"], fields.get("type"), fields["source_file"], __import__("time").time()),
            )
            conn.commit()

    def upsert_diagnosis(self, icd10: str, **fields: Any) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO kg_diagnoses (icd10, name, compatible_agents, source_file, created_at) VALUES (?,?,?,?,?)",
                (icd10, fields["name"], json.dumps(fields.get("compatible_agents", [])),
                 fields["source_file"], __import__("time").time()),
            )
            conn.commit()

    # ── 关系写入 ──

    def add_relation(self,
                     source_type: str, source_id: str,
                     relation_type: str,
                     target_type: str, target_id: str,
                     trust_level: str = "", evidence: str = "",
                     ) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR IGNORE INTO kg_relations (source_type, source_id, relation_type, target_type, target_id, trust_level, evidence, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (source_type, source_id, relation_type, target_type, target_id,
                 trust_level, evidence, __import__("time").time()),
            )
            conn.commit()

    def clear_relations(self) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM kg_relations")
            conn.commit()

    # ── 查询 ──

    def query_relations(self, source_type: str | None = None, relation_type: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._get_conn()
            q = "SELECT * FROM kg_relations"
            conds = []
            params: list[Any] = []
            if source_type:
                conds.append("source_type = ?")
                params.append(source_type)
            if relation_type:
                conds.append("relation_type = ?")
                params.append(relation_type)
            if conds:
                q += " WHERE " + " AND ".join(conds)
            return [dict(r) for r in conn.execute(q, params).fetchall()]

    def count_entities(self) -> dict[str, int]:
        with self._lock:
            conn = self._get_conn()
            counts = {}
            for table in ENTITY_TABLES:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                counts[table] = row[0]
            return counts

    def count_relations(self) -> int:
        with self._lock:
            conn = self._get_conn()
            return conn.execute("SELECT COUNT(*) FROM kg_relations").fetchone()[0]


_singleton_state: dict = {}


def get_kg_store() -> KGStore:
    from haip._singleton import locked_singleton
    return locked_singleton(KGStore, _singleton_state, "kg_store")
