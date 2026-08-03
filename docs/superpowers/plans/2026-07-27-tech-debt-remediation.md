# 技术债务修复计划 — xhaip v1.2 → v1.3

> 执行计划 | 2026-07-27 | 基线: `docs/superpowers/specs/2026-07-27-tech-debt-audit.md`

**Goal:** 消除两轮深度扫描确认的 22 项技术债务，按五层优先级分 Tier 执行，确保 v1.3 在安全性和架构完整性上零退化。

**Architecture:** 修复范围严格限定在单个模块/文件内，不改动 A2A dispatcher / registry / YAML loader / AgentLoop 等核心引擎。

**Tech Stack:** Python 3.10+ / pytest / ruff 0.8.6 / mypy 1.14.1 / FastAPI TestClient

**Spec:** `docs/superpowers/specs/2026-07-27-tech-debt-audit.md`

## Global Constraints

- ruff line-length=100, 修改文件必须 0 错误
- mypy 修改文件必须 0 错误
- 不引入新第三方依赖
- 不改动 A2A/registry/loader/agent YAML 核心引擎
- 每项修复有对应测试或验证命令
- 每 Task 结束 commit 一次
- 所有命令在 `D:\dst\projects\xhaip` 执行

---

## Task 1: L3-1 — Guard 验证异常 fail-closed (阻断项)

**Severity:** 严重 — Guard 内部任何异常都导致不安全输出通过

**Files:**
- Modify: `packages/haip-core/haip/guard/verifier.py`
- Create: `packages/haip-core/tests/test_guard_fail_closed.py`

**Interfaces:**
- Consumes: `GuardVerifier.verify()` 调用链 → `CitationEngine.validate()` → `ConfidenceScorer.score()`
- Produces: verify() 异常时 `GuardResult(status="error")` 而非 `status="pass"`

- [ ] **Step 1: 写失败测试**

```python
# packages/haip-core/tests/test_guard_fail_closed.py
"""Guard 异常场景: fail-closed 验证 — Guard 内部异常必须阻断通过."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from haip.guard.verifier import GuardVerifier


class TestGuardFailClosed:
    def test_citation_exception_blocks_pass(self):
        """Citation 引擎异常时, verify 应返回 error 而非 pass"""
        verifier = GuardVerifier()
        with patch.object(
            verifier._citation, "validate",
            side_effect=RuntimeError("citation crash")
        ):
            result = verifier.verify(content="test content", agent_name="test_agent")
            assert result.status != "pass"
            assert result.status == "error"
            assert "citation" in str(result.reason).lower() or result.status == "error"

    def test_confidence_exception_blocks_pass(self):
        """Confidence 评分异常时, verify 应返回 error 而非 pass"""
        verifier = GuardVerifier()
        with patch.object(
            verifier._confidence, "score",
            side_effect=ValueError("confidence crash")
        ):
            result = verifier.verify(content="test content", agent_name="test_agent")
            assert result.status != "pass"
            assert result.status == "error"

    def test_normal_flow_still_works(self):
        """正常流程不受影响"""
        verifier = GuardVerifier()
        result = verifier.verify(
            content="根据 NCCN 2023 指南，建议进行乳腺超声检查。",
            agent_name="breast-center",
            trigger="乳腺筛查"
        )
        assert result.status in ("pass", "warn", "block", "error")

    def test_none_content_blocks(self):
        """None 输入应被正确拦截"""
        verifier = GuardVerifier()
        result = verifier.verify(content=None, agent_name="test_agent")
        assert result.status != "pass"

    def test_empty_content_handled(self):
        """空内容不应导致 pass（至少 warn）"""
        verifier = GuardVerifier()
        result = verifier.verify(content="", agent_name="test_agent")
        assert result.status != "pass" or result.confidence.value < 0.5
```

- [ ] **Step 2: 运行确认失败**

```powershell
python -m pytest packages/haip-core/tests/test_guard_fail_closed.py -q
```
Expected: 至少 2 项 FAIL — `test_citation_exception_blocks_pass` + `test_confidence_exception_blocks_pass` 当前被降级通过

- [ ] **Step 3: 修复 guard/verifier.py**

`packages/haip-core/haip/guard/verifier.py` 中 `verify()` 方法的异常处理改为 fail-closed：

```python
# 当前行为 (line ~144):
# except Exception:
#     logger.debug("Guard 验证异常, 降级通过: %s", e)

# 改为:
except Exception:
    logger.exception("Guard 验证异常, 阻断通过")
    return GuardResult(
        status="error",
        reason="Guard 内部异常: 验证不可用",
        confidence=ConfidenceScore(value=0.0),
        citations=[]
    )
```

同时确认 `GuardResult` 支持 `status="error"` 状态；若不支持，新增该枚举值。

- [ ] **Step 4: 验证修复**

```powershell
python -m pytest packages/haip-core/tests/test_guard_fail_closed.py -q
```
Expected: 5 passed

- [ ] **Step 5: 回归**

```powershell
python -m pytest packages/haip-core/tests/test_guard.py packages/haip-core/tests/test_guard_gating.py packages/haip-core/tests/test_loop_guard.py -q
python -m ruff check packages/haip-core/haip/guard/verifier.py
python -m mypy packages/haip-core/haip/guard/verifier.py
```
Expected: 全部 passed, ruff=0, mypy=0

- [ ] **Step 6: Commit**

```powershell
git add packages/haip-core/haip/guard/verifier.py packages/haip-core/tests/test_guard_fail_closed.py
git commit -m "fix(guard): Guard 验证异常改为 fail-closed, 禁止降级通过"
```

---

## Task 2: L5-1 — signoff + session 多步事务原子性

**Severity:** 严重 — 临床数据更新与审计日志分两次 commit，半途失败不可回滚

**Files:**
- Modify: `packages/haip-core/haip/signoff.py`
- Modify: `packages/haip-core/haip/session/store.py`
- Modify: `packages/haip-core/tests/test_signoff.py`

**Interfaces:**
- Consumes: `SignoffManager.decide()` / `SessionService.append_event()`
- Produces: 同连接内多语句 + 单次 commit

- [ ] **Step 1: signoff.decide() 事务合并**

`packages/haip-core/haip/signoff.py` `decide()` 方法当前：

```python
# 当前: 两次 commit
conn.execute("UPDATE signoff_record SET ...")
conn.commit()                    # ← 第 1 次 commit
self._audit(signoff_id, ...)     # ← 内部再次 connect + commit
```

改为：

```python
# 修复: 同连接单 commit
conn.execute("UPDATE signoff_record SET ...")
self._audit(conn, signoff_id, ...)  # 传入已有连接
conn.commit()                       # ← 单次 commit，失败回滚全部
```

`_audit()` 新增可选参数 `conn=None`，传入时复用连接而非新建。

- [ ] **Step 2: session.append_event() 事务合并**

`packages/haip-core/haip/session/store.py` `append_event()` 当前：

```python
# 当前: 两次连接两次 commit
if event.state_delta:
    with self._get_conn() as conn:     # 连接 A
        conn.execute("UPDATE ...")
        conn.commit()
with self._lock, self._get_conn() as conn:  # 连接 B
    conn.execute("INSERT ...")
    conn.commit()
```

改为：

```python
# 修复: 单连接单 commit
with self._lock, self._get_conn() as conn:
    if event.state_delta:
        session.apply_delta(event.state_delta)
        conn.execute("UPDATE agent_sessions SET ...")
    conn.execute("INSERT INTO agent_events ...")
    conn.commit()
```

- [ ] **Step 3: 验证**

```powershell
python -m pytest packages/haip-core/tests/test_signoff.py packages/haip-core/tests/test_auth.py -q
python -m pytest packages/haip-core/tests/test_memory_runner.py -q
```
Expected: 全部 passed（现有 signoff/session 测试不依赖于两次独立 commit）

- [ ] **Step 4: lint + type check**

```powershell
python -m ruff check packages/haip-core/haip/signoff.py packages/haip-core/haip/session/store.py
python -m mypy packages/haip-core/haip/signoff.py packages/haip-core/haip/session/store.py
```
Expected: 0 errors

- [ ] **Step 5: Commit**

```powershell
git add packages/haip-core/haip/signoff.py packages/haip-core/haip/session/store.py
git commit -m "fix: signoff + session 多步写入改为同连接事务原子性"
```

---

## Task 3: L5-2 — TokenBucket 线程安全

**Severity:** 高 — FastAPI async 并发下 `_buckets` dict 读写竞态

**Files:**
- Modify: `packages/haip-core/haip/rate_limit.py`
- Create: `packages/haip-core/tests/test_rate_limit_race.py`

- [ ] **Step 1: 写并发测试**

```python
# packages/haip-core/tests/test_rate_limit_race.py
"""TokenBucket 并发安全性测试."""

from __future__ import annotations

import threading
import time

from haip.rate_limit import TokenBucket


def test_concurrent_consume_no_race():
    """10 个线程并发 consume 不应有竞态导致计数错误"""
    bucket = TokenBucket(rate=100, burst=20)
    results = []

    def worker():
        for _ in range(100):
            results.append(bucket.consume("test_user"))

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    allowed = sum(1 for r in results if r)
    denied = sum(1 for r in results if not r)
    assert allowed + denied == 1000
    assert allowed <= 120  # burst=20 + rate replenishment
```

- [ ] **Step 2: 运行确认失败**

```powershell
python -m pytest packages/haip-core/tests/test_rate_limit_race.py -q
```

- [ ] **Step 3: 修复 rate_limit.py**

`TokenBucket.consume()` 方法加 `threading.Lock`:

```python
class TokenBucket:
    def __init__(self, rate: float = 10.0, burst: int = 20, window: float = 1.0):
        self._rate = rate
        self._burst = burst
        self._window = window
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()

    def consume(self, key: str = "default") -> bool:
        now = time.monotonic()
        with self._lock:
            self._maybe_cleanup(now)
            timestamps = self._buckets.get(key, [])
            timestamps = [t for t in timestamps if now - t < self._window]
            if len(timestamps) >= self._burst:
                self._buckets[key] = timestamps
                return False
            timestamps.append(now)
            self._buckets[key] = timestamps
            return True
```

- [ ] **Step 4: 验证修复**

```powershell
python -m pytest packages/haip-core/tests/test_rate_limit_race.py -q --count=5
```
Expected: 5 runs × 全部 passed（无偶发失败）

- [ ] **Step 5: 回归**

```powershell
python -m ruff check packages/haip-core/haip/rate_limit.py
python -m mypy packages/haip-core/haip/rate_limit.py
```
Expected: 0 errors

- [ ] **Step 6: Commit**

```powershell
git add packages/haip-core/haip/rate_limit.py packages/haip-core/tests/test_rate_limit_race.py
git commit -m "fix(rate-limit): TokenBucket.consume() 加锁消除并发竞态"
```

---

## Task 4: L3-2 — 硬编码密钥治理

**Severity:** 高 — dev 默认密钥在生产启动时不报错

**Files:**
- Modify: `packages/haip-core/haip/crypto/__init__.py`
- Modify: `packages/haip-core/haip/auth/jwt.py`
- Modify: `packages/haip-core/haip/auth/__init__.py`
- Modify: `packages/haip-core/haip/security_baseline.py`

- [ ] **Step 1: crypto 移除默认密钥**

`packages/haip-core/haip/crypto/__init__.py`:

```python
# 当前 (line 45):
# key = os.environ.get("ENCRYPTION_KEY", "xhaip-dev-encryption-key-change-me")
# 改为:
key = os.environ.get("ENCRYPTION_KEY")
if not key:
    if os.environ.get("HAIP_ENV") == "production":
        raise RuntimeError("ENCRYPTION_KEY 必须设置")
    key = "xhaip-dev-encryption-key-change-me"  # 仅 dev 模式 fallback
```

- [ ] **Step 2: jwt 移除默认 secret**

`packages/haip-core/haip/auth/jwt.py`:

```python
# 当前 (line 19):
# _SECRET_KEY = "xhaip-dev-secret-change-in-production"
# 改为:
_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")
if not _SECRET_KEY:
    if os.environ.get("HAIP_ENV") == "production":
        raise RuntimeError("JWT_SECRET_KEY 必须设置")
    _SECRET_KEY = "xhaip-dev-secret-change-in-production"  # 仅 dev 模式 fallback
```

- [ ] **Step 3: auth 移除默认 demo password**

`packages/haip-core/haip/auth/__init__.py`:

```python
# 当前 (line 230):
# demo_password = os.environ.get("HAIP_DEMO_PASSWORD", "Demo@123456")
# 改为:
demo_password = os.environ.get("HAIP_DEMO_PASSWORD")
if not demo_password:
    if os.environ.get("HAIP_ENV") == "production":
        raise RuntimeError("HAIP_DEMO_PASSWORD 必须设置")
    demo_password = "Demo@123456"
```

- [ ] **Step 4: security_baseline 升级为阻断**

`packages/haip-core/haip/security_baseline.py` 中 `check_production_security()` 当前只 warn，改为：

```python
# 生产模式下未设置密钥 → raise SecurityBaselineError，启动即失败
# dev/test 模式下保持 warn
```

- [ ] **Step 5: 验证**

```powershell
python -m pytest packages/haip-core/tests/test_crypto.py packages/haip-core/tests/test_auth.py packages/haip-core/tests/test_security.py packages/haip-core/tests/test_production_profile.py -q
```
Expected: 全部 passed（test 模式自动走 dev 分支）

- [ ] **Step 6: Commit**

```powershell
git add packages/haip-core/haip/crypto/__init__.py packages/haip-core/haip/auth/jwt.py packages/haip-core/haip/auth/__init__.py packages/haip-core/haip/security_baseline.py
git commit -m "fix(security): 硬编码密钥改为 env-only + 生产启动即失败"
```

---

## Task 5: L4-1 — SQLite 迁移框架 (PRAGMA user_version)

**Severity:** 严重 — 12 个 SQLite 无 schema 版本管理

**Files:**
- Modify: `packages/haip-core/haip/database.py` (及所有使用 sqlite3 的模块)
- Create: `packages/haip-core/haip/schema_version.py`

**Strategy:** 不引入 Alembic（零新依赖），使用 `PRAGMA user_version` 管理 schema 版本，每个 DB 在连接初始化时执行 `_migrate(conn)` 检查版本号并执行增量迁移。

- [ ] **Step 1: 创建 schema_version.py**

```python
# packages/haip-core/haip/schema_version.py
"""SQLite schema 版本管理 — 基于 PRAGMA user_version"""

from __future__ import annotations

import logging
import sqlite3
from typing import Callable

logger = logging.getLogger(__name__)

MigrationFn = Callable[[sqlite3.Connection], None]


def get_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def set_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(f"PRAGMA user_version = {version}")


def migrate(conn: sqlite3.Connection, migrations: dict[int, MigrationFn], target: int) -> None:
    current = get_version(conn)
    for v in range(current + 1, target + 1):
        if v in migrations:
            logger.info("执行 schema 迁移: v%d → v%d", current, v)
            migrations[v](conn)
            set_version(conn, v)
            current = v
```

- [ ] **Step 2: database.py 接入**

`packages/haip-core/haip/database.py` `create_tables()` 改为先执行迁移再建表：

```python
from haip.schema_version import migrate

async def create_tables():
    async with _engine.begin() as conn:
        await conn.run_sync(lambda c: migrate(c, MIGRATIONS, CURRENT_VERSION))
        # ... 原有 CREATE TABLE IF NOT EXISTS ...
```

- [ ] **Step 3: 按模块逐步接入 (后续 Tasks)**

剩余 11 个模块在后续 v1.3 迭代中逐步接入 `schema_version.migrate()`。

- [ ] **Step 4: 验证**

```powershell
python -m pytest packages/haip-core/tests/test_database*.py -q
python -m ruff check packages/haip-core/haip/schema_version.py packages/haip-core/haip/database.py
python -m mypy packages/haip-core/haip/schema_version.py packages/haip-core/haip/database.py
```
Expected: 0 errors

- [ ] **Step 5: Commit**

```powershell
git add packages/haip-core/haip/schema_version.py packages/haip-core/haip/database.py
git commit -m "feat: SQLite PRAGMA user_version 迁移框架 (零新依赖)"
```

---

## Task 6: L2-1 — InMemorySessionService 添加 LRU 淘汰

**Severity:** 高 — session dict 永不淘汰，内存持续增长

**Files:**
- Modify: `packages/haip-core/haip/session/store.py`

- [ ] **Step 1: 实现 LRU**

`InMemorySessionService` 添加 `max_sessions` 参数 (default 1000) 和 TTL:

```python
class InMemorySessionService(SessionService):
    def __init__(self, max_sessions: int = 1000, session_ttl: float = 3600.0):
        self._sessions: dict[str, AgentSession] = {}
        self._access_times: dict[str, float] = {}
        self._max_sessions = max_sessions
        self._session_ttl = session_ttl
        self._lock = threading.Lock()

    def _evict_expired(self, now: float):
        expired = [
            sid for sid, t in self._access_times.items()
            if now - t > self._session_ttl
        ]
        for sid in expired:
            del self._sessions[sid]
            del self._access_times[sid]

    def _evict_lru(self):
        while len(self._sessions) >= self._max_sessions:
            oldest = min(self._access_times, key=self._access_times.get)
            del self._sessions[oldest]
            del self._access_times[oldest]
```

- [ ] **Step 2: 写淘汰测试**

```python
# 追加到 packages/haip-core/tests/test_runtime_a2a.py (或新建 test_session_eviction.py)
def test_session_eviction_by_cap():
    svc = InMemorySessionService(max_sessions=3)
    for i in range(5):
        svc.create_session(f"session_{i}")
    assert len(svc._sessions) <= 3

def test_session_eviction_by_ttl():
    svc = InMemorySessionService(session_ttl=0.1)
    svc.create_session("s1")
    time.sleep(0.2)
    svc._evict_expired(time.monotonic())
    assert "s1" not in svc._sessions
```

- [ ] **Step 3: 验证**

```powershell
python -m pytest packages/haip-core/tests/ -k "session" -q
```
Expected: 全部 passed

- [ ] **Step 4: Commit**

```powershell
git add packages/haip-core/haip/session/store.py
git commit -m "fix(session): InMemorySessionService 添加 LRU+TTL 淘汰"
```

---

## Task 7: L4-2 — permission 表添加索引

**Severity:** 高 — 7 张表零用户索引，核心查询全表扫描

**Files:**
- Modify: `packages/haip-core/haip/permission/__init__.py`

- [ ] **Step 1: 添加索引**

`PermissionManager._init_db()` 中在 `CREATE TABLE` 语句后追加:

```sql
CREATE INDEX IF NOT EXISTS idx_auth_user_role_user_id ON auth_user_role(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_role_agent_role_code ON auth_role_agent(role_code);
CREATE INDEX IF NOT EXISTS idx_perm_agent_call_target ON perm_agent_call_policy(target_agent_id);
CREATE INDEX IF NOT EXISTS idx_perm_data_agent ON perm_data_policy(agent_id);
CREATE INDEX IF NOT EXISTS idx_audit_access_timestamp ON audit_access_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_access_user ON audit_access_log(user_id);
```

- [ ] **Step 2: 验证**

```powershell
python -m pytest packages/haip-core/tests/test_permission.py packages/haip-core/tests/test_permission_singleton.py -q
python -m ruff check packages/haip-core/haip/permission/__init__.py
```
Expected: 全部 passed, ruff=0

- [ ] **Step 3: Commit**

```powershell
git add packages/haip-core/haip/permission/__init__.py
git commit -m "perf(permission): 7 张表添加查询索引"
```

---

## Task 8: L1-9 — backup_db.py 自动发现所有 *.db

**Severity:** 高 — 仅备份 3/12 个数据源

**Files:**
- Modify: `scripts/backup_db.py`

- [ ] **Step 1: 自动发现**

`scripts/backup_db.py` 中将硬编码的文件列表改为:

```python
DB_FILES = list(ROOT.rglob("*.db"))
DB_FILES += [ROOT / "packages" / "haip-hospital" / "data" / "patients.json"]
JSON_CONFIGS = list(ROOT.glob("config/*.yaml"))
```

- [ ] **Step 2: 添加恢复脚本**

新建 `scripts/restore_db.py`（基础版本）:

```python
"""恢复备份 — 将 releases/backups/<timestamp>/ 内容复制回原位"""
```

- [ ] **Step 3: 验证**

```powershell
python scripts/backup_db.py
python -m pytest tests/test_backup_script.py -q
```
Expected: backup 成功, 覆盖所有 *.db 文件, 测试 passed

- [ ] **Step 4: Commit**

```powershell
git add scripts/backup_db.py scripts/restore_db.py
git commit -m "fix(backup): 自动发现所有 *.db 文件 + 基础恢复脚本"
```

---

## Summary — 执行顺序与依赖

```
Task 1 (L3-1 Guard fail-closed)    ← 阻断项, 无依赖, 优先执行
  ↓
Task 2 (L5-1 事务原子性)           ← 阻断项, 无依赖
  ↓
Task 3 (L5-2 TokenBucket 锁)       ← 无依赖
Task 4 (L3-2 密钥治理)             ← 无依赖
  ↓
Task 5 (L4-1 迁移框架)             ← 基础设施, 后续接入依赖此 Task
  ↓
Task 6 (L2-1 session 淘汰)         ← 无依赖
Task 7 (L4-2 permission 索引)      ← 无依赖
Task 8 (L1-9 backup 自动发现)      ← 无依赖
```
