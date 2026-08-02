---
type: architecture
name: xhaip-core
description: xhaip v1.0 核心引擎。10 模块 (agent/a2a/llm/tools/guard/orchestrator/knowledge/loop/cli/matcher) + 14 YAML 驱动 Agent + 71 数据资产 + 196 测试/93% 覆盖率。
trust_level: T1
version: "1.0.0"
source:
  - packages/haip-core
  - docs/specs/xhaip-refactoring-design.md
---

# xhaip v1.0 核心引擎

## 引擎模块

| 模块 | 文件 | 覆盖率 | 职责 |
|------|------|--------|------|
| agent | `haip/agent/__init__.py` | 99% | DomainPlugin + YAML loader + Registry |
| agent/matcher | `haip/agent/matcher.py` | 新增 | 3 级降级匹配 (精确→子串→difflib) |
| a2a | `haip/a2a/__init__.py` | 98% | 进程内调度器 (auto-import-call-format) |
| llm | `haip/llm/` | 100% | LLMProvider 抽象 + DeepSeek + Mock |
| tools | `haip/tools/` | 100% | BaseTool + ToolResult + Registry |
| guard | `haip/guard/` | 90-94% | Citation + Confidence + 4-layer Verifier |
| orchestrator | `haip/orchestrator/` | 99% | TaskDAG + toposort_layers parallel |
| knowledge | `haip/knowledge/` | 99% | SQLite store + YAML sync |
| loop | `haip/loop/` | 100% | ReAct AgentLoop (LLM + Tool 循环) |
| cli | `haip/cli.py` | 91% | Typer CLI 统一入口 |

## 增强的 Agent 模块 (v1.1)

| Agent | 行数 | 函数 | 关键能力 |
|-------|------|------|---------|
| orthopedics | 392 | 9 | T2 8因素时机引擎 / 4维并发症 / 4阶段护理 / 随访 |
| cardio_risk | 153 | 3 | RCRI评分 / ECG 6模式库 / 围术期MI分型 |
| anesthesia | 116 | 4 | ASA分级 / 困难气道 / 抗凝桥接 / 麻醉方案 |
| pediatrics | 151 | 3 | 生长发育 / 8种药物剂量 / IMCI 8规则决策树 |
| acute_pain | 99 | 3 | NRS/VAS / PCA (年龄/肝肾调整) / 危象检测 |
| cancer_pain | 92 | 3 | WHO三阶梯 / 阿片安全(OD/DDI) / 姑息转介 |
| medical_record | 115 | 4 | 5个预置患者 / 检验查询 / 检查查询 / 搜索 |

## 数据资产 (71 文件)

| 类别 | 数量 | 路径 |
|------|------|------|
| 临床指南 | 26 | `knowledge/guidelines/` |
| 业务规则 | 22 | `knowledge/rules/` |
| 业务流程 | 11 | `knowledge/business_processes/` |
| 能力模型 | 3 | `knowledge/capabilities/` |
| 价值流 | 1 | `knowledge/value_streams/` |
| 架构实例 | 6 | `knowledge/architecture/` |
| 角色体系 | 1 | `knowledge/roles/` |
| 指南来源 | 1 | `knowledge/guideline_sources/` |

## 质量门禁

| 指标 | 值 |
|------|-----|
| 测试 | 196 |
| 覆盖率 | 93% |
| ruff | 0 |
| mypy | 0 |
