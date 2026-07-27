"""xhaip Permission System — A2A/A2D policy enforcement + SQLite store.

Bridged with existing auth/ (RBAC) and audit/ (AuditLogger).
Delegates role-based access to auth.rbac.has_permission().
Uses audit.AuditLogger for immutable audit trails.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Models ──────────────────────────────────────────────────


@dataclass
class PermissionContext:
    """调用上下文 — 携带身份信息。"""
    user_id: str = ""
    role: str = ""
    agent_id: str = ""
    department: str = ""
    is_emergency: bool = False


@dataclass
class AgentCallPolicy:
    """A2A 策略: 谁可以调哪个 Agent 的哪些工具."""
    caller_agent_id: str = ""
    caller_agent_type: str = ""
    target_agent_id: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    condition: str = ""
    priority: int = 0


@dataclass
class DataPolicy:
    """A2D 策略: Agent 能读哪些数据."""
    agent_id: str = ""
    agent_type: str = ""
    data_product: str = ""
    action: str = "read"
    field_filter: list[str] = field(default_factory=list)
    field_denylist: list[str] = field(default_factory=list)
    dept_scope: str = "self"  # self | all | consulted
    security_label: str = "NORMAL"
    requires_consent: bool = False


# ── Permission Manager ──────────────────────────────────────

# permission 的 ROLE_* 码 → auth/rbac (PREDEFINED_ROLES) 角色名桥接
_RBAC_ROLE_ALIASES: dict[str, str] = {
    "ROLE_PHYSICIAN": "doctor",
    "ROLE_SPECIALIST": "doctor",
    "ROLE_EMERGENCY": "doctor",
    "ROLE_ANESTHESIOLOGIST": "doctor",
    "ROLE_PHARMACIST": "pharmacist",
    "ROLE_NURSE": "nurse",
    "ROLE_ADMIN": "admin",
}


class PermissionManager:
    """角色 + 策略 权限管理。基于 SQLite 存储。"""

    def __init__(self, db_path: str = ":memory:"):
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    # ── Schema ──

    def _init_schema(self) -> None:
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS auth_user (
                user_id TEXT PRIMARY KEY, username TEXT, real_name TEXT,
                title TEXT, license_no TEXT, email TEXT, status TEXT DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS auth_role (
                role_code TEXT PRIMARY KEY, role_name TEXT, role_category TEXT
            );
            CREATE TABLE IF NOT EXISTS auth_user_role (
                user_id TEXT, role_code TEXT, PRIMARY KEY (user_id, role_code)
            );
            CREATE TABLE IF NOT EXISTS auth_agent (
                agent_id TEXT PRIMARY KEY, agent_name TEXT, agent_type TEXT,
                department_code TEXT, status TEXT DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS auth_role_agent (
                role_code TEXT, agent_id TEXT, PRIMARY KEY (role_code, agent_id)
            );
            CREATE TABLE IF NOT EXISTS perm_agent_call_policy (
                id INTEGER PRIMARY KEY, caller_agent_type TEXT, caller_agent_id TEXT,
                target_agent_id TEXT, allowed_tools TEXT, condition TEXT, priority INTEGER
            );
            CREATE TABLE IF NOT EXISTS perm_data_policy (
                id INTEGER PRIMARY KEY, agent_id TEXT, agent_type TEXT,
                data_product TEXT, action TEXT DEFAULT 'read',
                field_filter TEXT, field_denylist TEXT,
                dept_scope TEXT DEFAULT 'self', security_label TEXT DEFAULT 'NORMAL',
                requires_consent INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS audit_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_time TEXT DEFAULT (datetime('now')),
                subject_type TEXT, subject_id TEXT,
                action TEXT, resource_type TEXT, resource_id TEXT,
                decision TEXT, reason TEXT, metadata TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_auth_user_role_user_id ON auth_user_role(user_id);
            CREATE INDEX IF NOT EXISTS idx_auth_role_agent_role_code ON auth_role_agent(role_code);
            CREATE INDEX IF NOT EXISTS idx_perm_agent_call_target ON perm_agent_call_policy(target_agent_id);
            CREATE INDEX IF NOT EXISTS idx_perm_data_agent ON perm_data_policy(agent_id);
            CREATE INDEX IF NOT EXISTS idx_audit_access_timestamp ON audit_access_log(event_time);
            CREATE INDEX IF NOT EXISTS idx_audit_access_user ON audit_access_log(subject_id);
        """)

    # ── Seed ──

    def seed_defaults(self, agent_ids: list[str] | None = None,
                      include_dev_users: bool | None = None) -> None:
        """注入默认权限数据。

        Args:
            include_dev_users: 是否播种开发默认用户 (dr_001 等)。
                None 时读 HAIP_STRICT_SECURITY — strict 模式禁止 dev 数据入库。
        """
        if include_dev_users is None:
            import os
            include_dev_users = os.environ.get(
                "HAIP_STRICT_SECURITY", "").strip().lower() not in ("1", "true", "yes", "on")
        # Roles
        for code, name, cat in [
            ("ROLE_PHYSICIAN", "医师", "clinical"),
            ("ROLE_SPECIALIST", "专科医师", "clinical"),
            ("ROLE_PHARMACIST", "药师", "clinical"),
            ("ROLE_NURSE", "护士", "clinical"),
            ("ROLE_ANESTHESIOLOGIST", "麻醉师", "clinical"),
            ("ROLE_EMERGENCY", "急诊医师", "clinical"),
            ("ROLE_ADMIN", "管理员", "admin"),
        ]:
            self._db.execute(
                "INSERT OR IGNORE INTO auth_role VALUES (?,?,?)", (code, name, cat))

        # Default users (development only — strict 模式跳过)
        users = [
            ("dr_001", "张医师", "主治医师", "ROLE_PHYSICIAN"),
            ("pharm_001", "李药师", "临床药师", "ROLE_PHARMACIST"),
            ("nurse_001", "王护士", "护士长", "ROLE_NURSE"),
            ("admin_001", "管理员", "系统管理员", "ROLE_ADMIN"),
        ] if include_dev_users else []
        for uid, real_name, title, role in users:
            self._db.execute(
                "INSERT OR IGNORE INTO auth_user VALUES (?,?,?,?,NULL,NULL,'active')",
                (uid, uid, real_name, title))
            self._db.execute(
                "INSERT OR IGNORE INTO auth_user_role VALUES (?,?)", (uid, role))

        # Agent registration
        if agent_ids:
            for aid in agent_ids:
                self._db.execute(
                    "INSERT OR IGNORE INTO auth_agent VALUES (?,?,?,'','active')",
                    (aid, aid, "business"))

        # Default A2A policies: master_data agents are universally callable
        for target in ("medical-record", "metrics", "togaf"):
            self._db.execute(
                """INSERT OR IGNORE INTO perm_agent_call_policy
                   (caller_agent_type, target_agent_id, allowed_tools, priority)
                   VALUES ('*', ?, '*', 100)""",
                (target,))

        # Emergency agent has all-access
        self._db.execute(
            """INSERT OR IGNORE INTO perm_data_policy
               (agent_id, agent_type, dept_scope, security_label)
               VALUES ('emergency', 'business', 'all', 'EMERGENCY')""")

        self._db.commit()

    # ── U2A: User → Agent ──

    def get_user_roles(self, user_id: str) -> list[str]:
        rows = self._db.execute(
            "SELECT role_code FROM auth_user_role WHERE user_id=?", (user_id,))
        return [r[0] for r in rows]

    def get_accessible_agents(self, user_id: str) -> list[str]:
        roles = self.get_user_roles(user_id)
        if not roles:
            return []
        placeholders = ",".join("?" * len(roles))
        rows = self._db.execute(
            f"SELECT DISTINCT ra.agent_id FROM auth_role_agent ra WHERE ra.role_code IN ({placeholders})",
            roles)
        return [r[0] for r in rows]

    # ── A2A: Agent → Agent ──

    def can_call_agent(self, ctx: PermissionContext, target_agent: str, tool: str = "*") -> bool:
        """检查 caller 是否可以调用 target agent 的工具.

        优先级: A2A policy table > auth/rbac blanket check > fallback
        """
        if ctx.is_emergency:
            return True

        # 1. Check explicit A2A policies (per-agent granularity)
        has_explicit_policy = False
        rows = self._db.execute(
            """SELECT allowed_tools FROM perm_agent_call_policy
               WHERE (caller_agent_type='*' OR caller_agent_type=?)
                 AND (caller_agent_id='*' OR caller_agent_id=? OR caller_agent_id IS NULL)
                 AND target_agent_id=?
               ORDER BY priority DESC""",
            (ctx.agent_id, ctx.agent_id, target_agent))
        for r in rows:
            has_explicit_policy = True
            raw = r[0]
            if not raw:
                continue
            if raw == "*":
                return True
            try:
                allowed = json.loads(raw)
                if "*" in allowed or tool in allowed:
                    return True
            except (json.JSONDecodeError, TypeError):
                if str(raw) in (tool, "*"):
                    return True

        # 2. If explicit policy denied, no need to check RBAC
        if has_explicit_policy:
            return False

        # 3. Fall back to auth/rbac blanket check (桥接 ROLE_* 码与 rbac 角色名)
        try:
            from haip.auth.models import Permission
            from haip.auth.rbac import has_permission
            roles = [ctx.role]
            alias = _RBAC_ROLE_ALIASES.get(ctx.role)
            if alias:
                roles.append(alias)
            if has_permission(roles, Permission.AGENT_EXECUTE):
                return True
            return self._role_can_fallback(ctx.role, target_agent, tool)
        except ImportError:
            return self._role_can_fallback(ctx.role, target_agent, tool)

    def _role_can_fallback(self, role: str, agent: str, tool: str) -> bool:
        """Fallback role check when auth/rbac is not available."""
        if role == "admin":
            return True
        short_role = role.replace("ROLE_", "").lower()
        action = f"{agent}.{tool}"
        patterns: dict[str, list[str]] = {
            "physician": ["pharmacy.*", "orthopedic-surgery.*", "cardio-risk.*", "medical-record.*"],
            "pharmacist": ["pharmacy.*", "medical-record.*"],
            "nurse": ["medical-record.*"],
            "anesthesiologist": ["anesthesia-risk.*", "cardio-risk.*", "medical-record.*"],
        }
        for pattern in patterns.get(short_role, []):
            if pattern == "*" or (pattern.endswith(".*") and action.startswith(pattern[:-2])):
                return True
        return False

    # ── A2D: Agent → Data ──

    def can_access_data(self, ctx: PermissionContext, data_product: str,
                        patient_department: str = "") -> tuple[bool, list[str] | None]:
        """检查 Agent 是否可以访问数据产品。返回 (allowed, field_filter)."""
        if ctx.is_emergency:
            return True, None
        rows = self._db.execute(
            """SELECT dept_scope, field_filter, field_denylist, security_label, requires_consent
               FROM perm_data_policy
               WHERE (agent_id=? OR agent_type=?) AND data_product=?""",
            (ctx.agent_id, ctx.agent_id, data_product))
        for r in rows:
            dept_scope, ff, fd, sec_label, consent = r
            # Dept scope check
            if dept_scope == "self" and patient_department and ctx.department != patient_department:
                return False, None
            if dept_scope == "consulted":
                # fail-closed: 会诊范围需会诊记录支撑, 会诊表未实现前一律拒绝
                # (原实现 "simplified: allow for now" 属权限放水, 违反商用红线)
                return False, None
            # Field filter
            field_list = json.loads(ff) if ff and ff != "null" else None
            return True, field_list
        return True, None  # No policy → allow all (development default)

    # ── Audit ──

    def log_access(self, ctx: PermissionContext, action: str, resource: str,
                   decision: str, reason: str = "") -> None:
        # Write to SQLite schema
        self._db.execute(
            """INSERT INTO audit_access_log
               (subject_type, subject_id, action, resource_type, resource_id, decision, reason)
               VALUES (?,?,?,?,?,?,?)""",
            ("agent", ctx.agent_id or ctx.user_id, action,
             "agent_tool" if action == "A2A_call" else "data", resource,
             decision, reason))
        self._db.commit()
        # Also write to existing audit.AuditLogger
        try:
            from haip.audit import get_audit_logger
            get_audit_logger().log(
                action=action,
                resource=resource,
                status=decision,
                user_id=ctx.agent_id or ctx.user_id,
            )
        except ImportError:
            pass
        except Exception:
            logger.debug("audit.AuditLogger 写入失败", exc_info=True)

    # ── Helpers ──

    def can(self, role: str, action: str) -> bool:
        """Simple role-based check. Delegates to auth/rbac when available."""
        try:
            from haip.auth.models import Permission
            from haip.auth.rbac import has_permission
            return has_permission([role], Permission.AGENT_EXECUTE)
        except ImportError:
            return self._role_can_fallback(role, action, "*")

    def get_audit_logs(self, limit: int = 100, action: str = "") -> list[dict]:
        """审计记录查询 — 供审计处/管理后台使用。"""
        sql = "SELECT * FROM audit_access_log"
        args: list = []
        if action:
            sql += " WHERE action=?"
            args.append(action)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self._db.execute(sql, args)]

    def close(self) -> None:
        self._db.close()


# ── Global singleton ────────────────────────────────────────

_perm: PermissionManager | None = None


def _default_db_path() -> str:
    """默认持久化路径: <项目根>/data/permission.db。"""
    import os
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent.parent.parent
    data_dir = root / "data"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return ":memory:"
    return str(data_dir / "permission.db") if os.access(data_dir, os.W_OK) else ":memory:"


def get_permission_manager(db_path: str = "") -> PermissionManager:
    """进程级单例 (D2 修复: 禁止每次调用重建 + 审计必须落盘)。

    路径优先级: 显式参数 > 环境变量 HAIP_PERMISSION_DB > <root>/data/permission.db。
    HAIP_TEST_MODE=true 且未显式指定路径时使用 :memory: (保测试速度与隔离)。
    """
    global _perm
    if _perm is None:
        import os
        path = db_path or os.environ.get("HAIP_PERMISSION_DB", "")
        if not path:
            if os.environ.get("HAIP_TEST_MODE", "").strip().lower() == "true":
                path = ":memory:"
            else:
                path = _default_db_path()
        _perm = PermissionManager(path)
        _perm.seed_defaults()
    return _perm


def reset_permission_manager() -> None:
    """关闭并清空单例 (测试/重载用)。"""
    global _perm
    if _perm is not None:
        try:
            _perm.close()
        except (sqlite3.OperationalError, sqlite3.ProgrammingError, OSError):
            pass
        _perm = None


def get_permission(db_path: str = ":memory:") -> PermissionManager:
    """向后兼容别名 — 新代码请用 get_permission_manager()。"""
    return get_permission_manager(db_path if db_path != ":memory:" else "")
