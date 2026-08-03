# xhaip 资产所有权矩阵

> 每个资产目录的负责人、变更影响和通知机制

| 资产目录 | 负责人 | 变更影响范围 | 变更通知 |
|---------|--------|------------|---------|
| `packages/haip-core/haip/agent/` | 引擎团队 | 所有 Agent 加载 | CI (ruff + mypy + pytest) |
| `packages/haip-core/haip/a2a/` | 引擎团队 | 所有 Agent 间通信 | CI + integration tests |
| `packages/haip-core/haip/llm/` | 引擎团队 | 所有 Agent 推理 | CI |
| `packages/haip-core/haip/guard/` | 安全团队 | 所有 Agent 安全验证 | CI + 安全审计 |
| `packages/haip-core/haip/orchestrator/` | 引擎团队 | 多 Agent 编排 | CI + integration tests |
| `packages/haip-core/haip/knowledge/` | 知识团队 | 所有 Agent 知识查询 | CI |
| `packages/haip-core/haip/loop/` | 引擎团队 | 所有 Agent 推理循环 | CI |
| `packages/haip-core/haip/togaf/` | 架构团队 | TOGAF 治理 | CI + togaf validate |
| `packages/haip-hospital/agents/definitions/` | Agent 开发者 | 对应 Agent 行为 | CI + `xhaip list` |
| `packages/haip-hospital/modules/` | 临床专家 | 对应 Agent 决策逻辑 | PR review + integration tests |
| `packages/haip-hospital/knowledge/guidelines/` | 临床专家 | 引用该指南的 Agent | PR medical review |
| `packages/haip-hospital/knowledge/rules/` | 规则团队 | 引用该规则的 Agent | PR review + rule validation |
| `packages/haip-hospital/knowledge/business_processes/` | 流程专家 | 对应科室 Agent 流程 | PR review |
| `packages/haip-hospital/data/patients.json` | 数据团队 | 所有 Agent 测试数据 | CI + validate_patients.py |
| `.openharness/skills/` | Skill 维护者 | 引用该 skill 的 Agent | `xhaip sync-skills --validate` |
| `config/haip.yaml` | 平台运维 | 全局 Agent 加载 | PR review |
| `config/llm.yaml` | 平台运维 | 全局 LLM 配置 | PR review |
| `tests/integration/` | 测试团队 | 所有 Agent 集成验证 | CI |
| `scripts/` | 工程团队 | 自动化流程 | CI |

## 变更流程

1. 修改资产 → 通知对应负责人
2. 更新对应测试（单元/集成）
3. 运行 CI 全套门禁
4. 对于 `knowledge/guidelines/` 和 `knowledge/rules/` 变更，需临床/规则团队 review
5. 对于 `packages/haip-core/` 变更，需引擎团队 review
