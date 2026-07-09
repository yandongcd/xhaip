# AGENTS — xhaip (HAIP v1.0)

> 重构后的 Hospital AI Platform。老系统 `haip-0705-2/` 保持不变，所有新开发在 `xhaip/` 下进行。

## 快速开始

```bash
cd xhaip
pip install -e "packages/haip-core[dev]"
pytest packages/haip-core/tests/ tests/integration/ -v
ruff check packages/haip-core/ tests/
mypy packages/haip-core/haip/
```

## 架构

```
xhaip/
├── packages/haip-core/          # 核心引擎 (pip installable, 独立测试)
│   └── haip/
│       ├── agent/       DomainPlugin + YAML loader + Registry
│       ├── a2a/         Dispatcher (auto-import-call-format) + Router
│       ├── llm/         LLMProvider 抽象 + DeepSeek + Mock
│       ├── tools/       BaseTool + ToolResult + Registry
│       ├── guard/       CitationEngine + ConfidenceScorer + 4-layer Verifier
│       ├── orchestrator/ TaskDAG + toposort_layers + parallel executor
│       ├── knowledge/   SQLite store + YAML sync
│       ├── loop/        ReAct AgentLoop (LLM + Tool 循环)
│       └── cli.py       Typer CLI
│
├── haip-hospital/
│   ├── agents/definitions/      14 个 YAML Agent 定义 (30 行/个)
│   └── modules/                 14 个业务模块 (纯 Python, 只在写业务逻辑)
│
├── config/                      YAML 配置 (llm.yaml, haip.yaml)
├── tests/integration/           59 个集成测试
└── .github/workflows/ci.yml    CI: ruff + mypy + pytest + 90% cov
```

## 新增 Agent

只需两步：

### 1. 写 YAML 定义

```yaml
# agents/definitions/my-agent.yaml
name: my-agent
cn_name: 我的科室智能体
type: business
port: 8700

prompt:
  system: 你是一个医疗AI助手...
  temperature: 0.3

tools:
  - name: my_tool
    description: 工具描述
    handler: my_module.my_function
    input: {param1: str, param2: int}

guard:
  triggers: [药物交互]
```

### 2. 写业务模块

```python
# modules/my_module.py
def my_function(param1: str = "", param2: int = 0, **kwargs):
    return {"result": f"{param1} * {param2}", "status": "ok"}
```

**不需要**: 修改 `a2a_dispatcher.py`、`registry.py`、`agent_matcher.py`、写 `.bat` 文件。

## 测试

参照疼痛科 v0.2.0 的测试框架：

| 层级 | 模板文件 | 用途 |
|------|---------|------|
| 单元 | `test_acute_pain.py` | 核心业务函数 ≥ 3 场景 |
| A2A | `test_pain_a2a.py` | list_tools + 核心 tool 调用 |
| 异常 | `test_pain_exceptions.py` | 高危场景/异常输入 |
| YAML | `test_pain_yaml_validation.py` | YAML schema + rules 语法 |
| E2E | `test_pain_e2e.py` | 完整临床路径 |

测试要求：
- `haip-core` 覆盖率 ≥ 90%
- 每个新增 Agent 至少 3 个 A2A 调用测试
- MockProvider 用于隔离 LLM 依赖

## 质量门禁

```bash
ruff check packages/haip-core/ tests/     # 代码风格
mypy packages/haip-core/haip/             # 类型检查
pytest --cov=haip --cov-fail-under=90     # 单元测试 + 覆盖率
```

## 与 v0.2.0 的关键差异

| 场景 | v0.2.0 做法 | v1.0 做法 |
|------|-----------|----------|
| 新增 Agent | 创建 Python 子包 + 写 620 行胶水代码 + 改 3 个引擎文件 | 写 30 行 YAML + 写纯业务逻辑 |
| A2A 路由 | 手动改 `A2A_AGENTS` 字典 | 自动从 YAML 的 `handler` 字段生成 |
| LLM 切换 | 改 `llm.py` + `agent_loop.py` + `guard.py` 等 4+ 文件 | 改 1 行配置 `config/llm.yaml` |
| 测试 LLM | 需要真实 API key | MockProvider 返回 fixture，CI 可跑 |
| 编排执行 | `for node in dag.nodes` 顺序 | `toposort_layers()` 分层并行 |
