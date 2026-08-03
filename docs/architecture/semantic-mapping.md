# haip-0710 → xhaip 语义映射表

> 同一概念在 0710 和 xhaip 中的不同表达

| 概念 | haip-0710 (v0.2.0) | xhaip (v1.0) |
|------|-------------------|-------------|
| **Agent 定义** | Python 子包 + `DomainPlugin` + `__init__.py` | 单 YAML 文件 `agents/definitions/{name}.yaml` |
| **Agent 注册** | `pkgutil` 自动发现 `domains/` | YAML loader 自动解析 `definitions/` |
| **工具注册** | `tools.py` 中的 `TOOL_MANIFEST` 列表 | YAML `tools: [{name, handler}]` 字段 |
| **A2A 路由** | `a2a_dispatcher.py` 手动注册 `A2A_AGENTS` | YAML `handler` 字段 → `importlib` 自动生成 |
| **LLM 调用** | `urllib` 直连 DeepSeek API | `LLMProvider` ABC → DeepSeek / Mock |
| **编排模式** | `for node in dag.nodes` 顺序执行 | `toposort_layers()` 分层并行 |
| **知识库** | YAML 文件直读 | YAML → SQLite 同步（运行时毫秒级查询） |
| **引擎位置** | 嵌入 `src/agents/harness/` （业务代码同级） | 独立 pip 包 `packages/haip-core/` |
| **业务代码** | `src/agents/domains/haip/{agent}/` | `packages/haip-hospital/modules/{agent}/` |
| **患者数据** | 多文件 JSON/CSV | 单 `patients.json` + provenance |
| **Web 服务** | Python `http.server` + 模板 | FastAPI + uvicorn |
| **MCP 服务** | `generic_mcp_server.py` | `mcp_server.py` (SSE/JSON-RPC) |
| **CLI 框架** | Typer (`agents` 命令) | Typer (`xhaip` 命令) |
| **Agent 类型** | 5 类 (business/specialist/master_data/rules/architecture) | 简化 4 类 (business/specialist/master_data/architecture) |
| **版本管理** | 无正式版本契约 | `pyproject.toml` semver + YAML `version` |
| **CI 质量门** | 50% coverage + linter (52 rules) | 70% coverage + ruff + mypy |

## 废弃概念

以下 haip-0710 概念在 xhaip 中不再使用：

| 概念 | 废弃原因 |
|------|---------|
| `rules` Agent 类型 | 规则引擎并入 `haip-core/haip/togaf/rule_engine.py` |
| `metrics` 独立 Agent | 指标并入 `masterdata` 或知识库 |
| `agent_config.json` | 统一为 YAML definition 格式 |
| `ASSET_REGISTRY.md` | 由 YAML 文件系统 + `sync-skills` 自动管理 |
| Nexent Runtime SSE 协议 | xhaip 独立于 Nexent |
| NX 可视化域 | Nexent 耦合严重，保留 insight 子集 |
