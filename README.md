# xhaip — HAIP v1.2

> **Hospital AI Platform** — YAML 驱动的多 Agent 医院智能体平台。  
> v1.2: 补齐权限/审计/Guard 门控/Transport/Pre-LLM路由/Data Product，达到 PROD-READY。

## 合规状态

> **[PROD-READY]** 权限系统 (U2A/A2A/A2D) + 审计日志 + Guard 门控已实现。  
> Citation 强制 + 版本依赖校验 + T1/T2 信任强制执行已就位。  
> 患者数据均已脱敏，含 `provenance` 溯源。详见 `docs/architecture/DESIGN/permission-system.md`

## 快速开始

```bash
# 免安装自包含: 从仓库根目录直接运行 (sitecustomize.py 自动注入内部包路径)
python -m uvicorn haip.web_server:app
python -m pytest packages/haip-core/tests/ tests/ -v

# 数据质量检查
python scripts/validate_patients.py
```

> 可选: 需要打包分发时 `pip install -e "packages/haip-core[dev]"`（仅此场景需要）。

## 项目结构

```
xhaip/
├── packages/
│   ├── haip-core/              # 核心引擎 (pip installable)
│   │   └── haip/               # agent/a2a/llm/tools/guard/orchestrator/knowledge/togaf/
│   └── haip-hospital/          # 48 Agent (39 clinical + 7 specialist + 2 master_data)
│       ├── agents/definitions/ # YAML Agent 定义 (52 文件)
│       ├── modules/            # Handler 模块 + 骨科 8 engine (from haip-0710)
│       ├── knowledge/          # 19 BP + 70 指南 + 53 规则组 (314 条)
│       └── data/               # 498 位数字病人 (含 provenance 溯源)
├── docs/architecture/          # 三层架构文档 (CURRENT/DESIGN/REFERENCE)
├── data/sql/schemas/           # 模拟医院 SQL 参考 (from haip-0710)
├── scripts/                    # validate_patients.py 等工具
├── config/                     # llm.yaml + haip.yaml
└── .github/                    # CI 6-job + PR/Issue/SECURITY/CODEOWNERS (from haip-0710)
```

## 4 个核心原则

| 原则 | 收益 |
|------|------|
| **YAML 驱动 Agent** | 新增 Agent: 30 行 YAML + 纯业务逻辑 |
| **引擎独立包** | haip-core pip installable, 跨医院复用 |
| **LLM Provider 抽象** | 模型切换: 改 1 行配置, CI 可用 Mock |
| **知识库 SQLite** | YAML 保持版本化, 运行时毫秒级查询 |

## 质量门禁

| 指标 | 数值 |
|------|------|
| 测试 | 2909 |
| 覆盖率 (core) | 70% |
| ruff | 0 errors |
| mypy | 0 errors |
| 患者数据校验 | validate_patients.py (0 FAIL) |
| CI 流水线 | 6-job (validate/lint/unit/integration/coverage/docker) |

## v1.2 更新 (2026-07-12)

### Gap 补齐 (12 项 → 0 项未闭合)
- **权限系统**: SQLite RBAC (U2A/A2A/A2D) + 审计日志
- **Guard 门控**: GuardVerifier 从诊断 → 强制阻断 (citation/confidence/threshold)
- **Citation 强制**: Agent YAML `guard.citation` 字段支持 required/min_sources/min_trust
- **版本依赖**: `depends_on` 在运行时校验，不匹配时阻断
- **T1/T2 信任**: 高危场景强制 T1 引用检查
- **Transport 抽象**: AgentTransport ABC (InProcess/MCP/Mock) + 注册表
- **Pre-LLM 路由**: KeywordRouter — 关键词匹配零 token 快速通道
- **HITL 集成**: HITLHook — 高危决策暂停等人工确认
- **Data Product**: 适配器模式 DataProduct(DataSourceAdapter) 解耦 Agent×数据源
- **全量测试**: 2909 tests / 全量通过 (CI 6-job 门禁)

详见 `docs/architecture/gap-remediation-strategy.md`
