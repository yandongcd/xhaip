# xhaip — HAIP v1.0

Hospital AI Platform 重构版。基于 4 个核心原则从零重建。

## 快速开始

```bash
pip install -e "packages/haip-core[dev]"
python -m pytest packages/haip-core/tests/ tests/integration/ -v
```

## 项目结构

```
xhaip/
├── packages/
│   ├── haip-core/              # 核心引擎 (pip installable)
│   │   ├── haip/               # agent/ a2a/ llm/ tools/ guard/ orchestrator/ knowledge/
│   │   └── tests/              # 71 单元测试
│   └── haip-hospital/          # 14 个 Agent (5 business + 7 specialist + 2 master_data)
│       ├── agents/definitions/ # YAML Agent 定义 (30 行/个)
│       └── modules/            # 纯业务逻辑模块
├── tests/integration/          # 59 集成测试
├── config/                     # YAML 配置
└── .github/workflows/ci.yml    # CI: ruff + mypy + pytest + 70% cov
```

## 4 个核心原则

| 原则 | 收益 |
|------|------|
| **YAML 驱动 Agent** | 新增 Agent: 2 天 → 2 小时 |
| **引擎独立包** | haip-core pip installable, 跨医院复用 |
| **LLM Provider 抽象** | 模型切换: 改 1 行配置, CI 可用 Mock |
| **知识库 SQLite** | YAML 保持版本化, 运行时毫秒级查询 |

## 质量门禁

| 指标 | 数值 |
|------|------|
| 测试 | 130 |
| 覆盖率 | 81% |
| ruff | 0 errors |
| mypy | 0 errors |

## 与 v0.2.0 对比

| 维度 | v0.2.0 | v1.0 |
|------|--------|------|
| Agent 定义 | Python 子包 + 620 行胶水代码 | 30 行 YAML + 纯业务逻辑 |
| A2A 路由 | 硬编码 A2A_AGENTS | 自动从 YAML 生成 |
| 引擎位置 | 业务包内 | 独立 pip 包 |
| LLM 调用 | urllib 直连 | Provider 抽象 + retry + Mock |
| 编排 | 顺序 for | toposort 分层并行 |
| 测试 | ~5% | 130 tests, 81% core coverage |
| CI | 无 | ruff + mypy + pytest + 70% gate |
