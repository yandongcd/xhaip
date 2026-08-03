# Self-Harness v4 — 平台进化引擎

> 设计文档 | 2026-07-26 | xhaip v1.2 → v1.3

## 1. 愿景

将 self-harness 从"静态校验工具"升级为"平台持续进化神经系统"——五层递进，每一层既是独立的质量门禁，又是下一层的数据基础。

```
Layer 5: 进化大脑     Stage 13   自主修复 / A/B验证 / 知识演化
Layer 4: 质量情报     Stage 12   覆盖率 / 一致性 / 回归 / 性能
Layer 3: 安全合规     Stage 10-11 规则合规 / Guard有效性 / 系统完整性
Layer 2: 运行时验证   Stage 9    患者驱动A2A / 响应校验 / 故障指纹 / 性能基线
Layer 1: 静态完整性   Stage 1-8  当前v3能力 (import / YAML字段 / 角色等)
```

## 2. 架构总览

### 2.1 MetaHarness 阶段扩展

当前 8 阶段 → 扩展至 13 阶段：

| Stage | 层 | 名称 | 输入 | 输出 |
|-------|-----|------|------|------|
| 1-8 | L1 | 现有能力 | — | — |
| **9** | **L2** | **runtime_a2a** | agents + patients | pass/fail + timing |
| **10** | **L3** | **rule_compliance** | Stage 9 输出 + knowledge rules | compliance score + violations |
| **11** | **L3** | **guard_effectiveness** | high_risk agents + risk scenarios | guard命中率 + 漏报/误报 |
| **12** | **L4** | **quality_intelligence** | Stage 9-11 全域数据 | 覆盖率 + 一致性 + 性能矩阵 + 趋势 |
| **13** | **L5** | **autonomous_evolution** | Stage 9-12 故障数据 | auto-fixes + A/B result |

### 2.2 数据流

```
patients.json (10659) ──┐
agent YAML (58) ────────┤
                          ├→ Stage 9 (Runtime A2A) ──→ runtime_results table
knowledge rules (500+) ──┤                              │
guard configs ───────────┤                              ↓
                          ├→ Stage 10 (Rule Compliance) ──→ compliance_scores
                          │                              ↓
                          ├→ Stage 11 (Guard Audit) ──→ guard_metrics
                          │                              ↓
                          └→ Stage 12 (Quality Intel) ──→ dashboard

Stage 9-12 故障数据 ──→ Stage 13 (Auto Evolution) ──→ auto-PR / rollback
```

### 2.3 新增持久化

`xhaip_memory.db` 新增表：

```sql
CREATE TABLE IF NOT EXISTS runtime_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    tool TEXT NOT NULL,
    patient_id TEXT,
    status TEXT NOT NULL,       -- pass/fail/timeout/error
    elapsed_ms REAL,
    error_type TEXT,            -- timeout/type_error/guard_block/perm_denied/...
    error_message TEXT,
    response_summary TEXT,      -- 截断的返回内容
    expected_keys TEXT,         -- 预期字段清单 (JSON)
    missing_keys TEXT,          -- 缺失字段 (JSON)
    timestamp REAL NOT NULL
);
```

## 3. Stage 9 详细设计 — Runtime A2A 验证 (Layer 2)

### 3.1 职责

对 338 个 handler，每个用 3 位 compatible 患者真实调用，验证运行时正确性。

### 3.2 核心流程

```python
def _run_runtime_a2a(self) -> dict:
    tasks = []  # list of {agent, tool, params}
    
    for agent_name, agent in self._agents.items():
        patients = load_patients(agent_name, limit=3)
        for tool in agent.get("tools", []):
            for patient in patients[:3]:
                params = self._build_params(patient, tool)
                tasks.append({agent: agent_name, tool: tool["name"], params})
    
    # 4路并发
    results = self._execute_batch(tasks, max_workers=4, timeout=10)
    
    # 校验 + 持久化
    return self._validate_and_persist(results)
```

### 3.3 参数构建

`_build_params(patient, tool)` 从患者数据提取与 tool input schema 同名的字段：

```python
def _build_params(patient: dict, tool: dict) -> dict:
    input_schema = tool.get("input", {})
    params = {}
    for key in input_schema:
        if key in patient:
            params[key] = patient[key]
        elif key in patient.get("lab_results", {}):
            params[key] = patient["lab_results"][key]
    # 通用字段
    params.setdefault("patient_id", patient.get("patient_id", ""))
    return params
```

### 3.4 并发执行

使用 `a2a.call_batch()` 的 ThreadPoolExecutor，max_workers=4：

```python
def _execute_batch(self, tasks, max_workers=4, timeout=10) -> list[dict]:
    from haip.a2a import call_batch
    batch_input = [{
        "agent": t["agent"],
        "tool": t["tool"],
        "params": t["params"],
    } for t in tasks]
    return call_batch(batch_input, max_workers=max_workers)
```

### 3.5 响应校验规则

| 校验项 | 规则 | 严重度 |
|--------|------|--------|
| status | `resp.status == "ok"` | critical |
| result 非空 | `resp.result is not None` | critical |
| 预期字段 | handler 声明类型字段存在于 result | warn |
| 响应时间 | `elapsed_ms < 10000` | warn |
| 异常捕获 | 未抛出未捕获异常 | critical |

### 3.6 产出格式

```json
{
  "total": 1014,
  "passed": 980,
  "failed": 34,
  "score": 97,
  "failures": [{"agent": "...", "tool": "...", "patient": "...", "error": "..."}],
  "timing": {"p50_ms": 12, "p95_ms": 45, "p99_ms": 120},
  "by_agent": {"pharmacy": {total: 36, passed: 35, failed: 1}, ...}
}
```

## 4. Stage 10 详细设计 — 规则合规审计 (Layer 3a)

### 4.1 职责

取 Stage 9 中成功执行的输出，对每条输出调用知识库规则进行临床合规检查。

### 4.2 核心流程

```
Stage 9 A2A results (status=ok) ──→ for each result:
  ├─ KnowledgeRuntime.find_rules(department) → matching rules
  ├─ 对每条 Schema B 规则求值:
  │   condition.field → 从 A2A result 取对应路径值
  │   condition.operator → 比较
  │   condition.value → 判等/大于/小于/包含
  └─ 记录: 通过规则数 / 违反规则数 / 未覆盖规则数
```

### 4.3 规则求值引擎

支持 Schema B 的全部算子：

```python
OPERATORS = {
    "==": lambda a, b: a == b,
    ">":  lambda a, b: a > b,
    "<":  lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "contains": lambda a, b: b in str(a),
}
```

### 4.4 产出

```json
{
  "total_rules_checked": 520,
  "passed": 480,
  "violated": 25,
  "uncovered": 15,
  "score": 92,
  "top_violations": [
    {"rule_id": "AE001", "agent": "antiemetic", "action": "5-HT3重复使用未拦截"}
  ]
}
```

## 5. Stage 11 详细设计 — Guard 有效性 (Layer 3b)

### 5.1 职责

对定义了 `high_risk_scenarios` 的 agent，注入高风险场景验证 guard 是否真正触发。

### 5.2 核心流程

```python
for agent in agents_with_high_risk:
    for scenario in agent.guard.high_risk_scenarios:
        # 用 call_with_loop 走完整 ReAct + Guard
        result = call_with_loop(agent, scenario_query, max_steps=3)
        guard = result.get("guard", {})
        
        # 验证
        assert guard["passed"] == False        # 应被阻断
        assert len(guard.get("violations", [])) > 0
        assert guard.get("confidence", 1.0) < 0.3
```

### 5.3 正常场景对照

同时用低风险患者走同一 agent，验证 guard 不会误拦截健康场景。

### 5.4 产出

```json
{
  "total_scenarios": 68,
  "correctly_blocked": 60,
  "missed_blocks": 3,
  "false_positives": 5,
  "score": 88,
  "coverage": {"antiemetic": {"scenarios": 7, "blocked": 7, "missed": 0}}
}
```

## 6. Stage 12 详细设计 — 质量情报 (Layer 4)

### 6.1 覆盖率矩阵

```
Agent×科室 矩阵: 58 agents × 医院71科室树
→ 找出完全无 agent 覆盖的科室
→ 找出有 agent 但无规则/无患者数据的薄弱科室
```

### 6.2 跨 Agent 一致性

同一患者，骨科 + 麻醉 + 药剂 分别输出，检查对立词：
`("高风险","低风险") ("手术","保守") ("禁忌","适用")`

### 6.3 性能热力图

所有 handler 的 p50/p95/p99 响应时间、Token 消耗聚合为矩阵。

### 6.4 回归趋势

对比历史 snapshot，score 下跌超过 5% 自动告警。

## 7. Stage 13 详细设计 — 自主进化 (Layer 5)

### 7.1 升级 Proposer 输入

当前 proposer 从"静态 YAML 审计违规"生成提案 → 升级为从"runtime 故障指纹"生成提案。

### 7.2 代码级修复

Proposer 不仅建议 YAML 修改，还能生成 handler 代码补丁：

```
故障: antiemetic.bp_drug_prophylaxis → KeyError: 'weight'
诊断: handler 直接访问 params['weight']，但患者数据键名为 weight_kg
生成: params['weight'] → params.get('weight', params.get('weight_kg', 0))
A/B:  运行修复后 handler → 通过 → auto-commit
```

### 7.3 A/B 验证管道

```
base 分支 (当前代码) → eval → baseline_score
candidate 分支 (应用补丁) → eval → candidate_score
gate: candidate_score >= baseline_score + 所有 affected tests 通过
```

### 7.4 知识演化

规则触发频率统计 → 长期未触发的规则标记为 `suspected_stale` → 提示人工审查。

## 8. 实施计划

| 阶段 | Stage | 预估工期 | 依赖 |
|------|-------|---------|------|
| Phase 1 | Stage 9 (L2) | 当前 | 无 |
| Phase 2 | Stage 10-11 (L3) | Stage 9 完成 | Stage 9 |
| Phase 3 | Stage 12 (L4) | Stage 10-11 完成 | Stage 9-11 |
| Phase 4 | Stage 13 (L5) | Stage 12 完成 | Stage 9-12 |

## 9. 风险与约束

- **患者数据偏差**: 部分 agent compatible 患者 < 3 位 → 降级为全局采样
- **LLM 依赖**: Stage 11 需要 LLM 走 loop，CI 环境用 MockProvider
- **执行时间**: 338 handler × 3 患者 ≈ 1000 次 A2A 调用，预估 2-5 分钟
- **并发安全**: a2a.call_batch 已线程安全，无需额外锁
- **向后兼容**: 新增阶段均为可选 (run_proposer=False 时跳过 L3-L5)
