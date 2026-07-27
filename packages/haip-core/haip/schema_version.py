"""SQLite schema 版本管理 — 基于 PRAGMA user_version (零新依赖).

为 12 个独立 SQLite 数据库提供统一的 schema 版本追踪和增量迁移能力。
替代方案: Alembic (太重, 需新依赖 + 每个 DB 一个 env.py).

用法:
    from haip.schema_version import get_version, set_version, migrate

    conn = sqlite3.connect("my.db")
    migrate(conn, MIGRATIONS, target_version=2)

MIGRATIONS 格式: dict[version: int, fn: (sqlite3.Connection) -> None]
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable

logger = logging.getLogger(__name__)

MigrationFn = Callable[[sqlite3.Connection], None]


def get_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def set_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(f"PRAGMA user_version = {version}")


def migrate(
    conn: sqlite3.Connection,
    migrations: dict[int, MigrationFn],
    target: int,
) -> None:
    """增量执行 schema 迁移, 从当前版本到 target。

    每步迁移在一个事务中执行, 失败自动回滚。
    """
    current = get_version(conn)
    if current >= target:
        return

    for v in range(current + 1, target + 1):
        if v not in migrations:
            continue
        logger.info("执行 schema 迁移: v%d → v%d", current, v)
        try:
            conn.execute("BEGIN")
            migrations[v](conn)
            set_version(conn, v)
            conn.commit()
            current = v
        except Exception:
            conn.rollback()
            logger.exception("schema 迁移 v%d 失败, 已回滚", v)
            raise


def ensure_version(conn: sqlite3.Connection, target_version: int) -> int:
    """开放式版本追踪 — 记录当前 target_version, 不执行迁移.

    用于新表创建后标记版本号, 避免 "从 0 开始" 的差距问题.
    返回记录的版本号.
    """
    current = get_version(conn)
    if current < target_version:
        set_version(conn, target_version)
        conn.commit()
    return target_version
