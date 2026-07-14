"""MemoryService — 跨会话语义记忆 (SQLite + 关键词搜索).

支持:
  1. 添加记忆条目 (add_memory)
  2. 关键词搜索 (search_memory)
  3. 从 Session 自动提取记忆 (ingest_session)
  4. 记忆合并/去重 (consolidate)

使用场景:
  - 患者偏好跨会话记忆
  - 临床诊断历史参考
  - 药物过敏史持久化
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import sqlite3


@dataclass
class MemoryEntry:
    """一条跨会话记忆."""
    id: str = field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:12]}")
    content: str = ""
    category: str = ""         # patient / clinical / preference / knowledge
    importance: int = 5        # 1-10
    tags: list[str] = field(default_factory=list)
    source_session_id: str = ""
    user_id: str = "default"
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


SCHEMA_MEMORY = """
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    importance INTEGER NOT NULL DEFAULT 5,
    tags_json TEXT NOT NULL DEFAULT '[]',
    source_session_id TEXT NOT NULL DEFAULT '',
    user_id TEXT NOT NULL DEFAULT 'default',
    created_at REAL NOT NULL,
    last_accessed REAL NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_content ON memories(content);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content, category, tags, content=memories, content_rowid=rowid
);
"""


class MemoryService:
    """跨会话记忆服务.

    支持:
      - SQLite 持久化 + FTS5 全文搜索
      - 按重要性/类别/标签检索
      - 会话自动提取 (ingest_session)
    """

    def __init__(self, db_path: str | Path = ":memory:"):
        self._db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.executescript(SCHEMA_MEMORY)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接 — 对于 :memory: DB, 需要返回同一连接."""
        # :memory: 每次 connect 创建独立 DB, 需要特殊处理
        if self._db_path == ":memory:":
            if not hasattr(self, "_mem_conn") or self._mem_conn is None:
                self._mem_conn = sqlite3.connect(":memory:")
                self._mem_conn.row_factory = sqlite3.Row
                self._mem_conn.executescript(SCHEMA_MEMORY)
            return self._mem_conn

        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── CRUD ──

    def add_memory(self, entry: MemoryEntry) -> str:
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO memories(id, content, category, importance, tags_json,
                   source_session_id, user_id, created_at, last_accessed, access_count,
                   metadata_json)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.id, entry.content, entry.category, entry.importance,
                    json.dumps(entry.tags, ensure_ascii=False),
                    entry.source_session_id, entry.user_id,
                    entry.created_at, entry.last_accessed, entry.access_count,
                    json.dumps(entry.metadata, ensure_ascii=False),
                ),
            )
            conn.commit()
        return entry.id

    def get_memory(self, memory_id: str) -> MemoryEntry | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            if row is None:
                return None

            # Update access tracking
            conn.execute(
                "UPDATE memories SET last_accessed = ?, access_count = access_count + 1 WHERE id = ?",
                (time.time(), memory_id),
            )
            conn.commit()

            return self._row_to_entry(row)

    def search_memory(
        self,
        query: str,
        user_id: str = "default",
        category: str = "",
        min_importance: int = 0,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """搜索记忆 (全文搜索 + 关键词回退)."""
        with self._get_conn() as conn:
            # Try FTS5 first
            try:
                rows = conn.execute(
                    """SELECT m.* FROM memories m
                       JOIN memories_fts fts ON m.rowid = fts.content_rowid
                       WHERE memories_fts MATCH ? AND m.user_id = ?
                       ORDER BY m.importance DESC, m.last_accessed DESC
                       LIMIT ?""",
                    (query, user_id, limit),
                ).fetchall()

                if rows:
                    return [self._row_to_entry(r) for r in rows]
            except sqlite3.OperationalError:
                pass  # FTS5 not available

            # Fallback: keyword LIKE search
            conditions = ["content LIKE ?", "user_id = ?"]
            params: list = [f"%{query}%", user_id]

            if category:
                conditions.append("category = ?")
                params.append(category)
            if min_importance > 0:
                conditions.append("importance >= ?")
                params.append(min_importance)

            where = " AND ".join(conditions)
            rows = conn.execute(
                f"SELECT * FROM memories WHERE {where} ORDER BY importance DESC, last_accessed DESC LIMIT ?",
                (*params, limit),
            ).fetchall()

            return [self._row_to_entry(r) for r in rows]

    def list_by_category(self, category: str, user_id: str = "default",
                         limit: int = 50) -> list[MemoryEntry]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM memories WHERE category = ? AND user_id = ? ORDER BY created_at DESC LIMIT ?",
                (category, user_id, limit),
            ).fetchall()
            return [self._row_to_entry(r) for r in rows]

    def delete_memory(self, memory_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cur.rowcount > 0

    def clear_user(self, user_id: str) -> int:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
            conn.commit()
            return cur.rowcount

    # ── 会话提取 ──

    def ingest_session(
        self,
        session_events: list,
        user_id: str = "default",
        session_id: str = "",
        categories: dict[str, list[str]] | None = None,
    ) -> list[str]:
        """从 Session events 中提取关键信息作为记忆.

        categories: {"clinical": ["诊断", "治疗", "手术"], "patient": ["过敏", "偏好"]}
        """
        categories = categories or {
            "clinical": ["诊断", "治疗", "方案", "用药", "手术", "评估", "检查"],
            "patient": ["过敏", "病史", "偏好", "禁忌"],
            "preference": ["选择", "倾向", "期望"],
        }

        ids = []
        evt_list = session_events if hasattr(session_events, '__iter__') else []
        for evt in evt_list:
            content = ""
            role = ""

            if hasattr(evt, 'content'):
                content = evt.content
                role = getattr(evt, 'role', '')
            elif isinstance(evt, dict):
                content = evt.get('content', '')
                role = evt.get('role', '')

            if not content or role == 'user':
                continue

            # 分类匹配
            for cat, keywords in categories.items():
                for kw in keywords:
                    if kw in content:
                        entry = MemoryEntry(
                            content=content[:500],
                            category=cat,
                            importance=7 if cat in ("patient", "clinical") else 5,
                            tags=[kw],
                            source_session_id=session_id,
                            user_id=user_id,
                        )
                        ids.append(self.add_memory(entry))
                        break

        return ids

    def consolidate(self, user_id: str = "default") -> int:
        """合并重复/相似记忆，返回合并数量."""
        # 简单实现: 完全相同内容的记忆去重
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT content, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
                   FROM memories WHERE user_id = ?
                   GROUP BY content HAVING cnt > 1""",
                (user_id,),
            ).fetchall()

            count = 0
            for row in rows:
                ids = row["ids"].split(",")
                # 保留第一个，删除其余
                for dup_id in ids[1:]:
                    conn.execute("DELETE FROM memories WHERE id = ?", (dup_id,))
                    count += 1
            conn.commit()
        return count

    def stats(self, user_id: str = "default") -> dict[str, Any]:
        with self._get_conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
            by_cat = conn.execute(
                "SELECT category, COUNT(*) as cnt FROM memories WHERE user_id = ? GROUP BY category",
                (user_id,),
            ).fetchall()
            return {
                "total": total,
                "by_category": {r["category"]: r["cnt"] for r in by_cat},
            }

    @staticmethod
    def _row_to_entry(row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            content=row["content"],
            category=row["category"],
            importance=row["importance"],
            tags=json.loads(row["tags_json"]),
            source_session_id=row["source_session_id"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            last_accessed=row["last_accessed"],
            access_count=row["access_count"],
            metadata=json.loads(row["metadata_json"]),
        )
