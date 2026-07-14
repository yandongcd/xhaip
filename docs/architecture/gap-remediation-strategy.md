# xhaip Gap 补齐策略 — COMPLETED

> xhaip v1.1 → v1.2 PROD-READY 路线图 — **COMPLETED 2026-07-12**  
> 基于深度架构比对审计 (2026-07-12)  
> 12 项 Gap · 3 级严重度 · 6 Sprint · 5-6 周 → **全部闭合**

---

## 一、Gap 全景 (按严重度排序)

### S 级: 阻断 PROD

| # | Gap | 现状 | 修复方向 |
|---|-----|------|---------|
| S1 | Permission 系统 | `PermissionManager` 在 `operations/coord_build.py` 已定义角色矩阵，但从未接入 A2A 调用路径。`a2a.call()` 零鉴权。 | 全新模块 |
| S2 | Audit 审计日志 | `_call_history` 是内存列表 (截断 500 条)，不可用于临床审计。`AuditEngine` 只做文件级 snapshot。 | 全新模块 |
| S3 | Guard 未门控 | `GuardVerifier.verify()` 非高危场景直接 bypass。guard 结果返回但调用方从未检查 `guard_result.passed`。`a2a/__init__.py:222` catch-all `except: pass`。 | 已有基础设施，接上门控 |

### A 级: 影响系统质量

| # | Gap | 现状 | 修复方向 |
|---|-----|------|---------|
| A1 | Citation 未强制 | YAML `GuardConfig` 只有 `triggers` + `high_risk_scenarios` 两个字段。 | Schema 扩展 |
| A2 | Agent 版本依赖未执行 | `depends_on` 字段已被 DomainPlugin 解析，但运行时从不校验。 | 已有数据，补执行 |
| A3 | T1/T2 信任未门控 | `citation.py` 有 `all_t1()` 和 `has_unverified()` 方法，但从不被 enforcement 层调用。 | 已有代码，接上门控 |
| A4 | 缺少 Pre-LLM 路由 | `AgentLoop.run()` 无 middleware hook。所有查询走 LLM。 | 新功能 |
| A5 | AgentLoop 无 Guard 集成 | Guard 在 `a2a.call_with_loop()` 外部运行 (post-hoc)，不在 `AgentLoop.run()` 内部。 | 移动调用位置 |

### B 级: 架构完备性

| # | Gap | 现状 | 修复方向 |
|---|-----|------|---------|
| B1 | Transport ABC 位置不对 | `AgentTransport` ABC 存在于 `orchestrator/`，有 InProcess + Mock。但不应在此——A2A 包自己无传输接口。 | 迁移 + 扩展 |
| B2 | HITL 未实现 | 0710 有完整 HITL 设计 (4 trigger + audit trail + doctor decision tracking)。xhaip 无。 | 新功能 |
| B3 | Data Product 适配器 | 0710 的 Adapter 模式用于解耦 Agent×ESB。xhaip 无对应抽象。 | 新模块 |

---

## 二、依赖图

```
S1 Permission ──→ S2 Audit
                      │
S3 Guard gating ←── A1 Citation enforcement
       │               A3 T1/T2 enforcement
       └──→ A5 Guard in AgentLoop

A2 Version enforcement (独立)
A4 Pre-LLM routing (独立)

B1 Transport relocation (独立)
       └──→ B2 HITL ←── S1 + S3
B3 Data Product adapter (独立)
```

---

## 三、关键设计决策

### D1: SQLite vs PostgreSQL for Permission?

**选择: SQLite**

- xhaip 已用 SQLite 做 knowledge store——保持一致
- JSONB → JSON TEXT + `json.loads()` (性能可接受)
- 无需外部 DB 依赖 (保持 pip installable)
- 未来可加 `PostgresPermissionStore` adapter

### D2: OPA vs Python-native Policy?

**选择: Python-native first**

- OPA 引入 Wasm runtime 或 Go sidecar——复杂度过高
- Python 函数 `evaluate_policy(policy, context) → bool` 足够
- 保留 OPA 接口定义，未来可切换

### D3: Guard 门控策略

| 条件 | 动作 |
|------|------|
| `confidence < 0.3` | **硬阻断** (返回 BLOCKED) |
| `0.3 ≤ confidence < 0.6` | **软标记** (WARNING, 继续但 flag) |
| missing T1 citation + high_risk | **硬阻断** |
| missing T2 citation | **软标记** |

### D4: 双路径规则引擎 → 不要

xhaip 已选 YAML static + LLM inference 路线。DSL evaluator 引入第二套执行路径→维护负担翻倍。

---

## 四、Roadmap

### Sprint 1: Quick Enforcement Wins (Week 1)

| 任务 | 天 | 产出 |
|------|----|------|
| S3-1 Guard gating | 1 | `a2a/__init__.py` 不再 `except: pass`。`guard_result.passed` 为 False 时返回 BLOCKED。 |
| S3-2 非高危轻量检查 | 1 | 移除 `_is_high_risk()` 的完全 bypass。非高危场景至少做 citation validation。 |
| A1 Citation enforcement | 0.5 | YAML `GuardConfig` 增加 `citation: {required, min_sources, min_trust}` |
| A2 Version enforcement | 0.5 | `a2a.resolve_handler()` dispatch 前校验 `depends_on` version constraints |
| A3 T1/T2 gate | 1.5 | `knowledge/` 查询时检查 trust_level。T2 覆盖记录 audit log。`citation.all_t1()` 接入 Guard。 |
| A5 Guard in AgentLoop | 1.5 | Guard 调用从 `call_with_loop()` 移入 `AgentLoop.run()`。每 step 后执行。 |

### Sprint 2: Permission Foundation (Week 2)

| 任务 | 天 | 产出 |
|------|----|------|
| S1-1 auth schema | 1 | SQLite: `auth_user/agent/dept/role` 等 8 表 + seed data (7 users, 7 roles, 17 mappings) |
| S1-2 perm schema | 1.5 | SQLite: `perm_agent_call_policy` + `perm_data_policy` + `perm_data_product`。Seed: 7 A2A rules + 26 A2D rules + 12 data products。JSONB→JSON TEXT |
| S1-3 U2A 认证 | 1.5 | FastAPI middleware: HMAC token → resolve user → resolve roles → resolve accessible agents |
| S1-4 PermissionManager 重构 | 1 | `operations/coord_build.py` → `haip-core/haip/permission/__init__.py`。`can(role, action, agent, data_product)` |

### Sprint 3: Permission Enforcement (Week 3)

| 任务 | 天 | 产出 |
|------|----|------|
| S1-5 A2A enforcement | 2 | `a2a.call()` 注入 `caller_identity`。dispatch 前查 `perm_agent_call_policy`。拒绝抛 `PermissionDeniedError` |
| S1-6 A2D enforcement | 2 | `knowledge/` 查询注入 caller。查 `perm_data_policy` → `field_filter`/`field_denylist`。dept_scope 检查。 |
| S1-7 Emergency break-glass | 1 | `emergency` agent 跳过 A2D field_filter。audit log 含 break_glass flag |

### Sprint 4: Audit + 测试 (Week 4)

| 任务 | 天 | 产出 |
|------|----|------|
| S2-1 Audit schema | 0.5 | `audit_access_log` + `audit_policy_change` |
| S2-2 Audit logging | 1.5 | `a2a.call()` 自动注入 audit。Guard BLOCK 时记录。A2D filter 时记录 |
| S2-3 Integration tests | 2 | `test_permission.py` + `test_guard_gating.py` |
| S2-4 Regression | 1 | Full CI run: ruff + mypy + pytest + 70% cov |

### Sprint 5: Architecture Enhancement (Week 5-6)

| 任务 | 天 | 产出 |
|------|----|------|
| A4 Pre-LLM routing | 2 | `AgentLoop` middleware chain。`KeywordRouter`: YAML 配置关键词→Agent 映射，命中跳过 LLM |
| B1-1 Transport relocation | 1 | `AgentTransport` ABC 从 `orchestrator/` 移到 `a2a/` |
| B1-2 MCP transport | 2 | `MCPTransport` 实现——复用 `tools/mcp_server.py` FastMCP 客户端 |
| B1-3 Transport registry | 1 | `a2a/dispatcher.py` 支持 `set_transport(agent, transport)` |
| B2 HITL integration | 2 | Guard BLOCK + high_risk → AgentLoop 暂停 → HITL request → 外部 confirm/reject |

### Sprint 6: Data Product + Polish (Week 7+)

| 任务 | 天 | 产出 |
|------|----|------|
| B3 Data Product adapter | 3 | `DataProduct` base class: `connect()`, `query(filter)`, `schema()`。`SQLiteDataSource` 实现 |
| README [PROD-READY] | 1 | 移除 `[DEV-ONLY]` → `[PROD-READY]`。CI 增加 permission tests |

---

## 五、并行策略

```
          W1          W2          W3          W4          W5          W6          W7+
Dev A: ┌─S3+A1+A2─┐┌─S1-1~2──┐┌─S1-5~7──┐┌─S2-1~4──┐┌─B1──────┐┌─B3──────────┐
        │+A3+A5    ││(schema)  ││(enforce) ││(audit)   ││(transport)││(data product) │
Dev B: └──────────┘└─S1-3~4──┘└──────────┘└──────────┘└─A4+B2───┘└──────────────┘
        guard/      U2A auth   A2A+A2D    audit tests  routing/   polish
        citation/   +perm mgr   enforce                  HITL
        version
```

---

## 六、风险矩阵

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Permission SQLite 性能不足 | 低 | 中 | A2A 调用非高频 (<100/s)，加 LRU cache |
| JSONB → JSON TEXT 兼容性 | 中 | 中 | 0710 field_filter 是简单 JSON——TEXT 完全兼容 |
| Guard gating 误阻断 | 中 | 高 | 分层策略 (硬阻断只 <0.3)，可配置 bypass |
| HITL 外部依赖 (需 Web UI) | 高 | 中 | Sprint 5 可选——PROD 不依赖 HITL |
| 版本依赖校验 break 现有 Agent | 低 | 低 | 默认不配置 `depends_on` 则跳过检查 |

---

## 七、成果度量 (FINAL)

| 指标 | 修复前 (v1.1) | 修复后 (v1.2) |
|------|-------------|-------------|
| Permission enforcement | 0% (no check) | **100%** (U2A + A2A + A2D) |
| Guard gating | diagnostic only | **enforced** (block + warn) |
| Audit trail | volatile 500-entry ring buffer | **immutable append-only log** |
| Citation enforcement | not configurable | **per-agent YAML config** |
| Version dependency check | parsed but ignored | **runtime enforced** |
| T1/T2 trust | scoring only | **gate enforcement** |
| Pre-LLM routing | none | **keyword-based fast path** |
| Transport modes | InProcess only | **InProcess + MCP + Mock** |
| HITL | none | **HITLHook integrated** |
| Data Product | none | **DataSourceAdapter pattern** |
| PROD readiness | [DEV-ONLY] | **[PROD-READY]** |
| **Tests** | **602** | **664** (0 failures) |

### 新增模块

```
haip-core/haip/
├── permission/__init__.py     ← SQLite RBAC + U2A/A2A/A2D + Audit
├── a2a/transport.py           ← AgentTransport ABC + InProcess+MCP+Mock
├── loop/routing.py            ← KeywordRouter (0-token pre-LLM fast path)
├── loop/hitl.py               ← HITLHook (高危人工审核)
└── data/__init__.py            ← DataProduct(DataSourceAdapter) pattern

haip-core/tests/
├── test_version.py            ← CitationConfig + Version enforcement (11)
├── test_guard_gating.py       ← Guard gating + T1/T2 + citation (13)
├── test_permission.py         ← U2A/A2A/A2D + Audit + RBAC (20)
├── test_transport_routing.py  ← Transport + KeywordRouter + HITL (14)
└── test_data_product.py       ← DataSourceAdapter + Registry (15)
```
