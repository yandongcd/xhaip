# 技术债务审视报告 — xhaip v1.2 → v1.3

> 设计文档 | 2026-07-27 | self-harness v4 债务输入层

## 1. 愿景

对 xhaip v1.2 全仓进行两轮深度扫描（架构/数据/性能/运维），将发现的技术债务映射到 self-harness v4 的五层质量模型，识别当前各层的薄弱点，为 v1.3 稳定性提升和 Stage 9-13 自动化检测提供基线。

## 2. 架构总览

### 2.1 五层债务分布

```
Layer 5: 进化大脑     2 项 — 事务原子性 / 竞态条件
Layer 4: 质量情报     2 项 — 零迁移框架 / permission 零索引
Layer 3: 安全合规     2 项 — Guard 降级通过 / 硬编码密钥
Layer 2: 运行时表现   7 项 — 内存泄漏 / N+1 / 缓存绕过 / 文件重复读取
Layer 1: 静态完整性   9 项 — 分层违反 / 重复定义 / 巨型文件 / 线程安全

总计 22 项确认债务
```

### 2.2 数据流：债务发现 → 治理闭环

```
                    ┌─────────────────────────────────────┐
                    │  22 项债务 ← 两轮深度扫描基线        │
                    └──────────────┬──────────────────────┘
                                   │
    ┌──────────────┬───────────────┼───────────────┬──────────────┐
    ▼              ▼               ▼               ▼              ▼
  Stage 9       Stage 10        Stage 11       Stage 12      Stage 13
  运行时验证    规则合规        Guard审计     质量情报      自主进化
  ─────────     ────────       ─────────      ────────      ────────
  L2-1 内存泄漏  L5-1 无事务    L3-1 降级通过  L4-1 无迁移    L1-9 backup
  L2-2-L2-7                                        L4-2 零索引   L2-7 WAL统一
  性能项                                                         D10 运算符bug
                                                                D21 __import__
  ← 检测覆盖 7 项 →          ← 检测覆盖 1 项 →           ← 可自动修复 4 项 →
```

### 2.3 判断四象限方法论

| 判断 | 标志 | 含义 | 数量 |
|------|------|------|------|
| ✅ 确认入债 | 入债 | 真实债务，需制定修复计划 | **22** |
| 🔄 已有对策 | 对策 | 问题存在但已有 plan/spec 推进中 | 5 |
| ⚠️ 降级挂起 | 挂起 | 真实但低影响，或当前阶段不宜动 | 9 |
| ❌ 排除/误判 | 排除 | 刻意工程取舍或不符合实际 | 5 |

**排除项说明：**

| # | 原发现 | 排除理由 |
|---|--------|---------|
| 1 | Ruff 抑制 28 条规则 | 刻意工程取舍；BLE001 有 test_no_silent_except.py 补偿 |
| 2 | 0 个 .pyi 存根 | 全项目 inline annotation + `from __future__ import annotations` 是现代化做法 |
| 3 | 无 tox.ini / .coveragerc | CI 命令行已配置 `--cov-fail-under=70` |
| 4 | 零 Protocol 定义 | ABC 足够当前抽象层级，Protocol 属过度设计 |
| 5 | print() 在 CLI 工具中 | operations/ 和 tools/mcp_server.py 的 print 是正确的 CLI 输出 |

**已有对策（与现有 plans 交叉覆盖）：**

| # | 原发现 | 覆盖来源 |
|---|--------|---------|
| 1 | 覆盖率 75% < 85% 目标 | self-harness v4 Stage 9 + 12 |
| 2 | 静默 except: pass | CHANGELOG "D1 silent except elimination" — `test_no_silent_except.py` |
| 3 | mypy 配置过松 | self-harness v4 Stage 12 质量情报矩阵 |
| 4 | __init__.py 模块级副作用 | self-harness v4 Stage 1 静态完整性 |
| 5 | 去中心化 SQLite 存储 | 已知架构决策，转向 alembic 见 L4-1 |

## 3. 逐层详析

### 3.1 Layer 1 — 静态完整性 (9 项)

当前 self-harness v3 Stage 1-8 已覆盖 import 检查、YAML 字段校验、角色校验。以下为存量尚未覆盖的债务：

| ID | 项 | 文件/位置 | 严重度 | v4 能否检测 |
|----|----|-----------|--------|-----------|
| L1-1 | core→hospital 反向导入 9 处 | `web_server.py:1180-1236` | 严重 | Stage 1 import 方向检查 |
| L1-2 | KnowledgeAgent 硬编码 hospital 路径 | `knowledge_agent.py:25-27` | 高 | — |
| L1-3 | 3 种冲突错误处理模式 (dict/None/raise) | `a2a/` `orchestrator/` | 高 | — |
| L1-4 | `AgentTransport` ABC 重复定义 2 次 | `a2a/transport.py:15` + `orchestrator/__init__.py:73` | 中 | Stage 1 重复类检测 |
| L1-5 | 33 个模块 `__init__.py` >500 行 (最大 37KB) | `modules/*/__init__.py` | 中 | Stage 12 规模矩阵 |
| L1-6 | `__import__()` 替代 `importlib` | `sync_checks.py:81` `web_server.py:1026` | 中 | Stage 1 import lint |
| L1-7 | 5 模块 `check_same_thread=False` 不加锁 | `knowledge/` `audit/` `auth/` `signoff/` `permission/` | 中高 | — |
| L1-8 | `users` + `audit_events` 表双文件重复定义 | `database.py` vs `auth/__init__.py` + `audit/__init__.py` | 中 | Stage 12 schema drift |
| L1-9 | `backup_db.py` 仅覆盖 3/12 个 SQLite 数据源 | `scripts/backup_db.py` | 高 | — |

**L1-1 详析 — 反向导入：**

`web_server.py` 中 9 处 `from modules.orthopedics import ...`：
```
assess (1180)  evaluate (1187)  plan (1194)  evaluate_timing (1201)
predict_complications (1208)  mdt_aggregate (1215)  assess_pain (1222)
rehab_track (1229)  followup_plan (1236)
```
方案：将 `/api/v1/orthopedic/*` 路由提取到 hospital 侧 router 模块，core 侧 `app.include_router()` 注册。

### 3.2 Layer 2 — 运行时表现 (7 项)

self-harness v4 Stage 9（运行时 A2A 验证）设计为对 338 个 handler 用 3 位患者真实调用，记录 elapsed_ms + error_type。以下债务可通过 Stage 9 的 timing 基线自动暴露：

| ID | 项 | 文件/位置 | 严重度 | Stage 9 检测方式 |
|----|----|-----------|--------|-----------------|
| L2-1 | `InMemorySessionService._sessions` 无界增长 | `session/store.py:338` | 高 | 压力测试: 1000 次 SSE 后内存趋势 |
| L2-2 | `/api/patients/{agent}` 绕过现有 mtime 缓存 | `web_server.py:296` | 高 | 响应时间基线 >200ms 标识 |
| L2-3 | `/api/togaf/governance` 每次读全盘 58 YAML | `web_server.py:388-396` | 高 | 响应时间基线 >500ms 标识 |
| L2-4 | `_load_llm_config()` 每 ReAct 循环读盘 | `a2a/__init__.py:297-323` | 中 | 响应时间基线异常 |
| L2-5 | `append_event()` N+1 查询 (2N 次 DB 往返) | `session/store.py:251-276` | 中 | SQLite 操作计数异常 |
| L2-6 | `LLMGateway._rate_tracker` 过期键永不清理 | `llm/gateway.py:59` | 低 | 内存趋势 |
| L2-7 | SQLite WAL 模式 5 模块未开启 | `knowledge/` `memory/` `signoff/` `permission/` `rag/bm25/` | 低 | 写锁竞争统计 |

### 3.3 Layer 3 — 安全合规 (2 项)

self-harness v4 Stage 10-11 设计为规则合规检查 + Guard 有效性审计。以下为当前安全层面的确认债务：

| ID | 项 | 文件/位置 | 严重度 | Stage 检测方式 |
|----|----|-----------|--------|--------------|
| L3-1 | **Guard 验证异常降级通过** | `guard/verifier.py:144` | **严重** | Stage 11 Guard 审计：检测 silent-bypass 模式 |
| L3-2 | 硬编码密钥默认值 (dev key 作为 fallback) | `crypto/__init__.py:45,58` `auth/jwt.py:19` `auth/__init__.py:230` | 高 | Stage 10 规则：禁止非 env 来源的 key 字面量 |

**L3-1 详析 — 最危险发现：**

```python
# guard/verifier.py:144 — 当前行为
except Exception:
    logger.debug("Guard 验证异常, 降级通过: %s", e)
    # 任何 Guard 内部 bug 都导致不安全输出通过
```

这违反 fail-closed 原则。在生产中，Guard 内部任何异常（序列化错误、JSON 解析失败、网络超时）都会让未经校验的 LLM 输出直接返回给临床用户。

### 3.4 Layer 4 — 质量情报 (2 项)

self-harness v4 Stage 12 设计为全域数据质量矩阵。以下填补当前矩阵的盲区：

| ID | 项 | 文件/位置 | 严重度 |
|----|----|-----------|--------|
| L4-1 | 零数据库迁移框架 — 12 个独立 SQLite 无 schema 版本管理 | 全局 | 严重 |
| L4-2 | `permission/__init__.py` 7 张表零用户索引 | `permission/__init__.py` | 高 |

**L4-1 详析：**

所有 12 个模块使用 `CREATE TABLE IF NOT EXISTS`，无 Alembic、无 `PRAGMA user_version`、无 schema_version 追踪。如果 v1.3 需要添加/重命名列，不存在任何迁移机制。当前 SQLite 数据库分布：

| 模块 | 数据库文件 | 表数 |
|------|----------|------|
| `database.py` | `xhaip.db` | 3 |
| `memory.py` | `xhaip_memory.db` | 1 |
| `session/store.py` | `data/sessions.db` | 2 |
| `session/memory.py` | (动态路径) | 2 |
| `knowledge/__init__.py` | (动态路径) | 2 |
| `signoff.py` | `data/signoff.db` | 1 |
| `audit/__init__.py` | (独立路径) | 1 |
| `permission/__init__.py` | `data/auth.db` | 8 |
| `learning/store.py` | (动态路径) | 2 |
| `rag/vector_store.py` | (动态路径) | 1 |
| `rag/bm25.py` | (动态路径) | 1 |
| auth dual backend | `data/auth.db` | 与 permission 共用 |

### 3.5 Layer 5 — 进化大脑 (2 项)

self-harness v4 Stage 13 设计为自主修复 + A/B 验证。以下 2 项属 Stage 13 无法自动修复、必须人工干预的结构性债务：

| ID | 项 | 文件/位置 | 严重度 |
|----|----|-----------|--------|
| L5-1 | **多步业务无事务原子性** | `signoff.py:decide()` + `session/store.py:append_event()` | 严重 |
| L5-2 | **`TokenBucket.consume()` 非线程安全** | `rate_limit.py:36-61` | 高 |

**L5-1 详析：**

`signoff.py:decide()`:
```
UPDATE signoff_record (line 64-68) → commit
audit log write (line 70)         → 单独的 commit
→ 审计写入失败时 signoff 状态已提交，不可回滚
```

`session/store.py:append_event()`:
```
UPDATE agent_sessions (line 256-258) → connection A → commit
INSERT agent_events (line 261-274)   → connection B → commit
→ 事件可能部分写入，session 与 event 脱钩
```

## 4. Alpha 评级建议

基于五层审视，建议 v1.3 发布采用以下 α 评级门槛：

| α 级 | 定义 | 待清零 |
|------|------|--------|
| α1 | alpha 内部测试 | L3-1 Guard 修复 (阻断) |
| α2 | beta 内部验证 | + L5-1 事务原子性 |
| α3 | 预发布 | + L3-2 密钥治理 + L4-1 迁移框架 |
| α4 | 正式发布 | + 全部 22 项 |

**当前建议：α4 — v1.3 release 前必须清零 Tier 1 (L3-1 Guard 降级) + Tier 2 (L5-1 无事务)**

## 5. 对 self-harness v4 的增强建议

基于债务审视，对 self-harness v4 设计提出 4 项增强：

### 5.1 Stage 11 Guard Audit 增强

当前设计：统计 guard 命中率 + 漏报/误报。
新增检测规则：
- 扫描 `except Exception.*降级` 模式 → 标记为 `silent_bypass`
- 对每个高风险 agent 注入异常场景（JSON 格式错误 / 超时 / None 返回），验证 Guard 是否正确 fail-closed

### 5.2 Stage 9 Runtime A2A 增强

当前设计：per-handler 调用 + 记录 elapsed_ms。
新增：session 生命周期压力测试 — 连续 1000 次 SSE 连接建立+断开，检测 `_sessions` dict 是否线性增长（未淘汰）。

### 5.3 Stage 12 Quality Intelligence 增强

当前设计：覆盖率 + 一致性 + 性能矩阵。
新增两项：
- **schema drift 检测** — 对比 12 个 SQLite 初始化模块的 CREATE TABLE 语句，检测重复定义 + 列差异
- **索引覆盖率** — 检测所有 WHERE/JOIN 子句中的字段是否在对应表上有索引

### 5.4 新增：备份完整性检查 (Stage 10 规则合规)

校验 `scripts/backup_db.py` 的文件发现列表是否覆盖项目内所有 `*.db` 文件（通过 `git ls-files` 或 `glob` 自动对比）。遗漏时标记为规则违规。

## 6. 附录：全量审视矩阵

### 第一轮扫描（8 领域 × 16 项）

| # | 发现 | 判断 | 对应 L |
|---|------|------|--------|
| 1 | 硬编码 dev 密钥 | ✅ L3-2 | L3 |
| 2 | 静默 except: pass (9 处) | 🔄 已有对策 | — |
| 3 | `os.environ` 被 `api_key_store.py` 直接修改 | ⚠️ 降级 | — |
| 4 | 安全基线仅警告 | ✅ 合并至 L3-2 | L3 |
| 5 | `from typing import Any` 泛滥 50+ 文件 | ⚠️ 降级 | — |
| 6 | 33 个巨型 `__init__.py` | ✅ L1-5 | L1 |
| 7 | mypy 配置过松 | 🔄 已有对策 | — |
| 8 | `__import__()` 2 处 | ✅ L1-6 | L1 |
| 9 | 覆盖率 75% < 85% | 🔄 已有对策 | — |
| 10 | hospital 无 mypy | ⚠️ 降级 | — |
| 11 | 90+ 处 `except Exception` | ⚠️ 降级 | — |
| 12 | `print()` 替代 logger | ⚠️ 降级 | — |
| 13 | Ruff 抑制 28 条规则 | ❌ 排除 | — |
| 14 | 0 个 .pyi 存根 | ❌ 排除 | — |
| 15 | 无 tox.ini / .coveragerc | ❌ 排除 | — |
| 16 | `__init__.py` 模块级副作用 | 🔄 已有对策 | — |

### 第二轮 — 架构扫描（8 项）

| # | 发现 | 判断 | 对应 L |
|---|------|------|--------|
| A1 | web_server 反向导入 hospital | ✅ L1-1 | L1 |
| A2 | KnowledgeAgent 硬编码路径 | ✅ L1-2 | L1 |
| A3 | 3 种冲突错误处理模式 | ✅ L1-3 | L1 |
| A4 | Guard 降级通过 | ✅ L3-1 | L3 |
| A5 | 11 文件各自 CREATE TABLE | 🔄 已有对策 | — |
| A6 | AgentTransport 重复定义 | ✅ L1-4 | L1 |
| A7 | 业务逻辑硬编码 | ⚠️ 降级 | — |
| A8 | 零 Protocol 定义 | ❌ 排除 | — |

### 第二轮 — 数据扫描（11 项）

| # | 发现 | 判断 | 对应 L |
|---|------|------|--------|
| B1 | SQL 注入 `data/__init__.py:58` | ⚠️ 降级 | — |
| B2 | 零数据库迁移 | ✅ L4-1 | L4 |
| B3 | backup 仅 3/12 数据源 | ✅ L1-9 | L1 |
| B4 | 多步业务无事务 | ✅ L5-1 | L5 |
| B5 | permission 表零索引 | ✅ L4-2 | L4 |
| B6 | session/store.py N+1 | ✅ L2-5 | L2 |
| B7 | users/audit_events 重复定义 | ✅ L1-8 | L1 |
| B8 | 运算符优先级 bug | ⚠️ 降级 | — |
| B9 | check_same_thread 不加锁 | ✅ L1-7 | L1 |
| B10 | WAL 不一致 | ✅ L2-7 | L2 |
| B11 | raw sqlite3 连接池缺失 | ⚠️ 降级 | — |

### 第二轮 — 性能/运维扫描（12 项）

| # | 发现 | 判断 | 对应 L |
|---|------|------|--------|
| C1 | patients API 绕过缓存 | ✅ L2-2 | L2 |
| C2 | InMemorySessionService 内存泄漏 | ✅ L2-1 | L2 |
| C3 | TokenBucket 竞态 | ✅ L5-2 | L5 |
| C4 | TOGAF API 每请求读全盘 | ✅ L2-3 | L2 |
| C5 | 无 SIGTERM 信号处理 | ⚠️ 降级 | — |
| C6 | Dockerfile.agent HEALTHCHECK bug | ⚠️ 降级 | — |
| C7 | docker-compose 无日志轮转 | ⚠️ 降级 | — |
| C8 | CI 密钥扫描排除 DEEPSEEK_API_KEY | ⚠️ 降级 | — |
| C9 | LLM 配置每 ReAct 循环读盘 | ✅ L2-4 | L2 |
| C10 | requirements-lock 无同步机制 | ⚠️ 降级 | — |
| C11 | LLMGateway rate_tracker 不清理 | ✅ L2-6 | L2 |
| C12 | 无 Docker volume | ⚠️ 降级 | — |
