# haip-0710 → xhaip 路径映射表

> haip-0710 文档中引用的路径在 xhaip 中的对应位置

| haip-0710 路径 | xhaip 路径 | 说明 |
|---------------|-----------|------|
| `src/agents/harness/` | `packages/haip-core/haip/` | 引擎核心 |
| `src/agents/domains/haip/` | `packages/haip-hospital/modules/` | 业务模块 |
| `src/agents/domains/haip/{agent}/core/` | `packages/haip-hospital/modules/{agent}/` | Agent handler 模块 |
| `src/agents/domains/haip/{agent}/tools.py` | YAML `tools[].handler` 字段 | 工具注册方式 |
| `src/agents/domains/haip/{agent}/web/server.py` | FastAPI `web_server.py` 路由 | Web UI |
| `src/agents/domains/togaf/` | `packages/haip-core/haip/togaf/` | TOGAF 治理模块 |
| `src/agents/rules/` | `packages/haip-core/haip/togaf/rule_engine.py` | 规则引擎 |
| `agents domain run --name` | `xhaip call --agent` | CLI 入口 |
| `agents validate` | `xhaip list` | 验证命令 |
| `agents sync-skills` | `xhaip sync-skills` | 技能同步 |
| `agents release` | `xhaip release` | 发布管理 |
| `agents arch audit` | `xhaip togaf validate` | 架构审计 |
| `ASSET_REGISTRY.md` | YAML definitions 自动注册 | 资产注册机制 |
| `agent_config.json` | `agents/definitions/{agent}.yaml` | Agent 配置格式 |
| `A2A_AGENTS` 字典 | YAML `tools[].handler` 自动发现 | A2A 路由 |
| `DomainPlugin` 注册 | YAML definition + pkgutil 自动发现 | Agent 注册 |
| `.openharness/skills/` | `.openharness/skills/` | 技能目录（不变） |
| `data/sql/` | `xhaip/data/sql/` (参考文档) | SQL 模拟医院 |
| `data/patients/synthetic/` | `xhaip/data/patients_relational/` | 患者关系型数据 |
