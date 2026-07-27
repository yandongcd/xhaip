"""医生签核工作流 — AI 建议 → 复核 → 采纳/驳回 → 留痕 (商用 M3 / 临床 C1).

设计:
  - SQLite 持久化 (路径: HAIP_SIGNOFF_DB > <root>/data/signoff.db)
  - 驳回必填理由; 决定不可二次修改 (病历留痕原则)
  - 每次决定同步写入 permission 审计库 (action=SIGNOFF, D2 管道复用)
"""

from __future__ import annotations

import logging
import sqlite3
import uuid

logger = logging.getLogger(__name__)

_VALID_DECISIONS = ("approved", "rejected")


class SignoffManager:
    """签核单存储与生命周期管理。"""

    def __init__(self, db_path: str = ":memory:"):
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS signoff_record (
                id TEXT PRIMARY KEY,
                created_at TEXT DEFAULT (datetime('now')),
                agent TEXT, tool TEXT, patient_id TEXT,
                output_summary TEXT, risk_level TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                reviewer_id TEXT, decided_at TEXT, reason TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_signoff_status ON signoff_record(status);
            CREATE INDEX IF NOT EXISTS idx_signoff_patient ON signoff_record(patient_id);
        """)

    # ── 生命周期 ──

    def create(self, agent: str = "", tool: str = "", patient_id: str = "",
               output_summary: str = "", risk_level: str = "medium") -> str:
        sid = uuid.uuid4().hex[:12]
        self._db.execute(
            """INSERT INTO signoff_record (id, agent, tool, patient_id, output_summary, risk_level)
               VALUES (?,?,?,?,?,?)""",
            (sid, agent, tool, patient_id, output_summary[:2000], risk_level))
        self._db.commit()
        return sid

    def decide(self, signoff_id: str, reviewer_id: str, decision: str,
               reason: str = "") -> dict:
        if decision not in _VALID_DECISIONS:
            raise ValueError(f"非法决定: {decision} (仅支持 {_VALID_DECISIONS})")
        if decision == "rejected" and not reason.strip():
            raise ValueError("驳回必须填写理由 (病历留痕要求)")
        if not reviewer_id.strip():
            raise ValueError("必须提供 reviewer_id")
        rec = self.get(signoff_id)
        if rec is None:
            raise ValueError(f"签核单不存在: {signoff_id}")
        if rec["status"] != "pending":
            raise ValueError(f"签核单已定 ({rec['status']}), 不可二次修改")
        self._db.execute("BEGIN")
        try:
            self._db.execute(
                """UPDATE signoff_record
                   SET status=?, reviewer_id=?, reason=?, decided_at=datetime('now')
                   WHERE id=?""",
                (decision, reviewer_id, reason, signoff_id))
            self._audit(signoff_id, reviewer_id, decision, reason)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        result = self.get(signoff_id)
        assert result is not None
        return result

    # ── 查询 ──

    def get(self, signoff_id: str) -> dict | None:
        row = self._db.execute(
            "SELECT * FROM signoff_record WHERE id=?", (signoff_id,)).fetchone()
        return dict(row) if row else None

    def list_pending(self, limit: int = 100) -> list[dict]:
        return [dict(r) for r in self._db.execute(
            "SELECT * FROM signoff_record WHERE status='pending' ORDER BY created_at DESC LIMIT ?",
            (limit,))]

    def list_by_patient(self, patient_id: str, limit: int = 100) -> list[dict]:
        return [dict(r) for r in self._db.execute(
            "SELECT * FROM signoff_record WHERE patient_id=? ORDER BY created_at DESC LIMIT ?",
            (patient_id, limit))]

    # ── 审计 ──

    def _audit(self, signoff_id: str, reviewer_id: str, decision: str, reason: str) -> None:
        try:
            from haip.permission import PermissionContext, get_permission_manager
            ctx = PermissionContext(user_id=reviewer_id, role="ROLE_PHYSICIAN")
            get_permission_manager().log_access(
                ctx, "SIGNOFF", f"signoff/{signoff_id}", decision, reason)
        except Exception as e:
            logger.warning("签核审计写入失败 %s: %s", signoff_id, e)

    def close(self) -> None:
        self._db.close()


# ── 单例 ──

_signoff: SignoffManager | None = None


def _default_db_path() -> str:
    import os
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent.parent
    data_dir = root / "data"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return ":memory:"
    return str(data_dir / "signoff.db") if os.access(data_dir, os.W_OK) else ":memory:"


def get_signoff_manager(db_path: str = "") -> SignoffManager:
    """进程级单例。路径优先级: 显式参数 > HAIP_SIGNOFF_DB > <root>/data/signoff.db。"""
    global _signoff
    if _signoff is None:
        import os
        path = db_path or os.environ.get("HAIP_SIGNOFF_DB", "") or _default_db_path()
        _signoff = SignoffManager(path)
    return _signoff


def reset_signoff_manager() -> None:
    global _signoff
    if _signoff is not None:
        try:
            _signoff.close()
        except Exception:
            pass
        _signoff = None
