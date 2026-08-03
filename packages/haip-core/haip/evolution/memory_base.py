"""进化记忆基础 — 案例库 + 经验库统一存储 (SQLite + 向量检索).

SEAL (Agent Hospital) 机制移植, 增强版:
- 案例库: 成功诊疗轨迹 (含金标准匹配), 按任务分库
- 经验库: 失败反思产出的结构化经验, 带验证闸门状态机
- 检索: BGE-M3 embedding + VectorStore (复用 haip.rag)

与 SEAL 的差异 (基于深挖结论):
1. 经验为结构化字段 (trigger/rule/action), 非纯自然语言 → 可验证可审计
2. 经验带验证状态 (pending/validated/rejected) + 审批回滚
3. 案例检索支持有用性评分 (SEAL B.3 未用于案例的 idea)
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DEFAULT_DB = Path(__file__).resolve().parent.parent.parent.parent / "xhaip_memory.db"


@dataclass
class CaseEntry:
    """成功诊疗案例."""

    case_id: str
    agent: str
    task: str
    question: str          # 场景/问题文本 (检索用)
    answer: dict[str, Any]  # 决策结果
    gold: dict[str, Any]    # 金标准
    matched: bool = True
    created_at: float = field(default_factory=time.time)


@dataclass
class ExperienceEntry:
    """失败反思产出的经验 (结构化)."""

    exp_id: str
    agent: str
    trigger: str           # 触发条件 (文本描述, 可检索)
    rule: str              # 决策建议
    action: str            # 具体行动
    source_failure: str    # 失败案例摘要
    status: str = "pending"  # pending → validated → approved/rejected
    trials: int = 0        # 验证试验次数
    pass_count: int = 0    # 通过次数
    created_at: float = field(default_factory=time.time)
    verified_at: float = 0.0


class EvolutionMemory:
    """案例库 + 经验库统一存储与检索."""

    def __init__(self, db_path: str = ""):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self._vector: tuple[Any, Any] | None = None
        self._vector_tried: bool = False
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS case_base (
                    case_id TEXT PRIMARY KEY,
                    agent TEXT NOT NULL,
                    task TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    gold TEXT NOT NULL,
                    matched INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_case_agent ON case_base(agent, task)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experience_base (
                    exp_id TEXT PRIMARY KEY,
                    agent TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    rule TEXT NOT NULL,
                    action TEXT NOT NULL,
                    source_failure TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    trials INTEGER NOT NULL DEFAULT 0,
                    pass_count INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    verified_at REAL NOT NULL DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_exp_agent ON experience_base(agent)")
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

    # ── 向量检索 ──

    def _vector_store(self) -> tuple[Any, Any] | None:
        """惰性创建向量存储 (BGE-M3, 失败时 None → 退化为关键词检索)."""
        import os
        if self._vector is not None:
            return self._vector
        if self._vector_tried:
            return None
        self._vector_tried = True
        if os.environ.get("HAIP_TEST_MODE", "") == "true":
            return None  # 测试环境避免模型下载
        try:
            from haip.rag import VectorStore, get_embedding_provider
            provider = get_embedding_provider()
            if provider.ready():
                store = VectorStore(db_path=str(self.db_path))
                if store.ready:
                    self._vector = (store, provider)
                    return self._vector
        except Exception:
            pass
        return None

    def _embed(self, text: str) -> list[float] | None:
        vs = self._vector_store()
        if not vs:
            return None
        _, provider = vs
        try:
            return provider.encode_single(text)
        except Exception:
            return None

    # ── 案例库 ──

    def add_case(self, entry: CaseEntry) -> str:
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO case_base (case_id, agent, task, question, answer, gold, matched, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (entry.case_id, entry.agent, entry.task, entry.question,
                 json.dumps(entry.answer, ensure_ascii=False),
                 json.dumps(entry.gold, ensure_ascii=False),
                 1 if entry.matched else 0, entry.created_at),
            )
            conn.commit()
        vs = self._vector_store()
        if vs:
            emb = self._embed(entry.question)
            if emb:
                try:
                    vs[0].insert_batch([{
                        "id": f"case_{entry.case_id}", "content_type": f"case_{entry.agent}",
                        "text": entry.question, "embedding": emb, "metadata": entry.case_id,
                    }])
                except Exception:
                    pass
        return entry.case_id

    def search_cases(self, agent: str, question: str, k: int = 3) -> list[dict[str, Any]]:
        """检索相似案例 (向量优先, 关键词兜底), 带有用性评分."""
        vs = self._vector_store()
        if vs:
            emb = self._embed(question)
            if emb:
                try:
                    rows = vs[0].search(emb, content_type=f"case_{agent}", k=k)
                    results = []
                    for r in rows:
                        meta = r.get("metadata", "")
                        case = self.get_case(meta) if meta else None
                        if case:
                            results.append({**case, "similarity": r.get("score", 0.0)})
                    if results:
                        return results
                except Exception:
                    pass
        # 关键词兜底 (query 分词, 任一命中, 忽略空格)
        kws = [k.replace(" ", "") for k in question.replace("，", ",").split(",") if len(k.strip()) >= 2]
        if not kws:
            kws = [question.replace(" ", "")[:20]]
        with self._lock:
            conn = self._get_conn()
            results = []
            for kw in kws[:5]:
                rows = conn.execute(
                    "SELECT * FROM case_base WHERE agent = ? ORDER BY created_at DESC",
                    (agent,),
                ).fetchall()
                for r in rows:
                    q = (r["question"] or "").replace(" ", "")
                    if kw in q and all(x.get("case_id") != r["case_id"] for x in results):
                        results.append(self._row_to_case(r))
                if len(results) >= k:
                    break
        return results[:k]

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        with self._lock:
            conn = self._get_conn()
            row = conn.execute("SELECT * FROM case_base WHERE case_id = ?", (case_id,)).fetchone()
        return self._row_to_case(row) if row else None

    def count_cases(self, agent: str = "") -> int:
        with self._lock:
            conn = self._get_conn()
            if agent:
                return conn.execute("SELECT COUNT(*) FROM case_base WHERE agent = ?", (agent,)).fetchone()[0]
            return conn.execute("SELECT COUNT(*) FROM case_base").fetchone()[0]

    @staticmethod
    def _row_to_case(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "case_id": row["case_id"], "agent": row["agent"], "task": row["task"],
            "question": row["question"],
            "answer": json.loads(row["answer"]),
            "gold": json.loads(row["gold"]),
            "matched": bool(row["matched"]), "created_at": row["created_at"],
        }

    # ── 经验库 ──

    def add_experience(self, entry: ExperienceEntry) -> str:
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO experience_base "
                "(exp_id, agent, trigger, rule, action, source_failure, status, trials, pass_count, created_at, verified_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (entry.exp_id, entry.agent, entry.trigger, entry.rule, entry.action,
                 entry.source_failure, entry.status, entry.trials, entry.pass_count,
                 entry.created_at, entry.verified_at),
            )
            conn.commit()
        return entry.exp_id

    def list_experiences(self, agent: str = "", status: str = "") -> list[dict[str, Any]]:
        with self._lock:
            conn = self._get_conn()
            q = "SELECT * FROM experience_base"
            params: list[Any] = []
            conds = []
            if agent:
                conds.append("agent = ?")
                params.append(agent)
            if status:
                conds.append("status = ?")
                params.append(status)
            if conds:
                q += " WHERE " + " AND ".join(conds)
            q += " ORDER BY created_at DESC"
            rows = conn.execute(q, params).fetchall()
        return [self._row_to_exp(r) for r in rows]

    def update_experience(self, exp_id: str, **fields: Any) -> None:
        allowed = {"status", "trials", "pass_count", "verified_at", "rule", "action"}
        sets = [f"{k} = ?" for k in fields if k in allowed]
        if not sets:
            return
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                f"UPDATE experience_base SET {', '.join(sets)} WHERE exp_id = ?",
                [fields[k] for k in fields if k in allowed] + [exp_id],
            )
            conn.commit()

    def get_experience(self, exp_id: str) -> dict[str, Any] | None:
        with self._lock:
            conn = self._get_conn()
            row = conn.execute("SELECT * FROM experience_base WHERE exp_id = ?", (exp_id,)).fetchone()
        return self._row_to_exp(row) if row else None

    @staticmethod
    def _row_to_exp(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "exp_id": row["exp_id"], "agent": row["agent"], "trigger": row["trigger"],
            "rule": row["rule"], "action": row["action"], "source_failure": row["source_failure"],
            "status": row["status"], "trials": row["trials"], "pass_count": row["pass_count"],
            "created_at": row["created_at"], "verified_at": row["verified_at"],
        }


_singleton_state: dict = {}


def get_evolution_memory() -> EvolutionMemory:
    from haip._singleton import locked_singleton
    return locked_singleton(EvolutionMemory, _singleton_state, "evolution_memory")
