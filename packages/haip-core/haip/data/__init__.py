"""Data Product Adapter — 解耦 Agent × 数据源。

来自 haip-0710 的设计思想: Agent 不直接访问 HIS/EMR/LIS，
通过 DataProduct(adapter) 抽象层查询数据。换数据源只需换 adapter。

Usage:
    from haip.data import DataProduct, DataSourceAdapter, get_registry
    reg = get_registry()
    reg.register(DataProduct(name="DP-HIS-PATIENT", adapter=SQLiteDataSource(...)))
    product = reg.get("DP-HIS-PATIENT")
    results = product.query({"patient_id": "P001"})
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ── Data Source Adapter ───────────────────────────────────────

class DataSourceAdapter(ABC):
    """数据源适配器 — 统一的数据访问接口。"""

    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def query(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """查询数据。返回记录列表。"""
        ...

    @abstractmethod
    def schema(self) -> dict[str, Any]:
        """返回数据源的 schema 定义。"""
        ...


class SQLiteDataSource(DataSourceAdapter):
    """SQLite 数据源适配器 — 复用 knowledge store 或独立数据库。"""

    def __init__(self, db_path: str = ":memory:", table: str = "", query_template: str = ""):
        import sqlite3
        self.db_path = db_path
        self.table = table
        self.query_template = query_template
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        import sqlite3
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

    def query(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        if self._conn is None:
            self.connect()
        sql = self.query_template or f"SELECT * FROM {self.table} WHERE 1=1"
        conditions = []
        values: list[Any] = []
        for k, v in params.items():
            conditions.append(f"{k}=?")
            values.append(v)
        if conditions and "WHERE" not in sql.upper():
            sql += " AND " + " AND ".join(conditions)
        elif conditions:
            sql += " AND " + " AND ".join(conditions)
        cursor = self._conn.execute(sql, values) if self._conn else None
        if cursor is None:
            return []
        return [dict(r) for r in cursor.fetchall()]

    def schema(self) -> dict[str, Any]:
        return {
            "type": "sqlite",
            "db_path": self.db_path,
            "table": self.table,
        }

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


class MockDataSource(DataSourceAdapter):
    """Mock 数据源 — 测试用。"""

    def __init__(self, data: list[dict[str, Any]] | None = None):
        self.data = data or []
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def query(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        results = self.data
        for k, v in params.items():
            results = [r for r in results if r.get(k) == v]
        return results

    def schema(self) -> dict[str, Any]:
        return {"type": "mock", "count": len(self.data)}


# ── Data Product ──────────────────────────────────────────────

@dataclass
class DataProduct:
    """数据产品 — 带 schema + 安全标签 + 适配器的数据访问单元。"""
    name: str = ""
    description: str = ""
    security_label: str = "NORMAL"  # NORMAL | SENSITIVE | RESTRICTED
    owner_department: str = ""
    adapter: DataSourceAdapter | None = None
    field_schema: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def query(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if self.adapter is None:
            return []
        return self.adapter.query(params or {})

    def get_schema(self) -> dict[str, Any]:
        if self.adapter is None:
            return self.field_schema
        return self.adapter.schema()


# ── Registry ──────────────────────────────────────────────────

class DataProductRegistry:
    """数据产品注册中心。"""

    def __init__(self) -> None:
        self._products: dict[str, DataProduct] = {}

    def register(self, product: DataProduct) -> None:
        self._products[product.name] = product

    def get(self, name: str) -> DataProduct | None:
        return self._products.get(name)

    def list_all(self) -> list[str]:
        return list(self._products.keys())

    def list_by_department(self, department: str) -> list[DataProduct]:
        return [p for p in self._products.values()
                if p.owner_department == department]

    def list_by_security(self, max_label: str) -> list[DataProduct]:
        """返回安全级别 ≤ max_label 的产品。"""
        levels = {"NORMAL": 0, "SENSITIVE": 1, "RESTRICTED": 2}
        max_level = levels.get(max_label, 0)
        return [p for p in self._products.values()
                if levels.get(p.security_label, 0) <= max_level]

    def seed_defaults(self) -> None:
        """注入预定义的数据产品（来自 haip-0710 设计）。"""
        defaults = [
            ("DP-HIS-PATIENT", "患者基本信息", "SENSITIVE", "全院"),
            ("DP-HIS-VISIT", "就诊/入院记录", "SENSITIVE", "全院"),
            ("DP-LIS-LAB", "检验结果", "SENSITIVE", "检验科"),
            ("DP-LIS-BG", "血气分析", "SENSITIVE", "检验科"),
            ("DP-PACS-EXAM", "检查申请与结果", "SENSITIVE", "影像科"),
            ("DP-PACS-IMAGE", "影像报告 (RIS)", "RESTRICTED", "影像科"),
            ("DP-EMR-NOTE", "病程记录", "RESTRICTED", "全院"),
            ("DP-EMR-DISCHARGE", "出院小结", "RESTRICTED", "全院"),
            ("DP-EMR-MED", "医嘱处方", "SENSITIVE", "全院"),
            ("DP-NIS-ASSESS", "护理评估", "SENSITIVE", "护理部"),
            ("DP-NIS-VITAL", "生命体征", "NORMAL", "护理部"),
        ]
        for name, desc, sec_label, owner in defaults:
            self.register(DataProduct(
                name=name, description=desc,
                security_label=sec_label, owner_department=owner,
            ))


# ── Global ────────────────────────────────────────────────────

_registry: DataProductRegistry | None = None


def get_registry() -> DataProductRegistry:
    global _registry
    if _registry is None:
        _registry = DataProductRegistry()
        _registry.seed_defaults()
    return _registry
