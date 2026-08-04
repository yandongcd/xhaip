# AGENTS — xhaip (HAIP v1.2)

> 重构后的 Hospital AI Platform。v1.2 补齐 (Permission/Guard gating/Citation/Transport/HITL/Data Product)。  
> 架构文档: `docs/architecture/INDEX.md` | 路径映射: `docs/architecture/path-mapping.md`  
> **[PROD-READY]** 权限系统 (U2A/A2A/A2D) + 审计日志已实现。

## 快速开始

```bash
cd xhaip
python -m pytest packages/haip-core/tests/ tests/ -v   # 免安装: sitecustomize.py 自动注入内部路径
python -m ruff check .
python -m mypy packages/haip-core/haip/
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
│       ├── togaf/       TOGAF 10 Architecture Governance (16 modules)
│       └── cli.py       Typer CLI
│
├── haip-hospital/
│   ├── agents/definitions/      83 个 YAML Agent 定义
│   ├── modules/                 81 个 Handler 模块 (KnowledgeAgent + RuleEngine 驱动)
│   ├── knowledge/               19 BP YAML + 100 指南 + 22 规则组 (237 条)
│   └── data/                    10659 位数字病人 (含专科检验字段)
│
├── config/                      YAML 配置 (llm.yaml, haip.yaml)
├── tests/                       2909 测试 (1503 haip-core + 1406 root)
└── .github/workflows/ci.yml    CI: ruff + mypy + pytest + 70% cov

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

## Skills & MCP Tools

### Skill 同步

xhaip 技能（Skills）存储在 `.openharness/skills/`，由源模块中的 SKILL.md 文件同步而来。

```bash
xhaip sync-skills               # 预览变更 (dry-run)
xhaip sync-skills --apply       # 执行同步
xhaip sync-skills --validate    # 校验一致性
xhaip sync-skills --init        # 初始化 (runtime → source，反向)
xhaip sync-skills --list        # 列出所有已注册 skill
```

**约定**:
- 每个 skill 属于源模块中的一个 SKILL.md 文件
- 源是唯一事实来源，runtime 是镜像
- 技能所有权通过 `SKILL_OWNERSHIP` 注册表管理（`haip/operations/skill_sync.py`）
- 支持自动发现 `packages/` 下的 SKILL.md 文件

**当前注册**:
| Skill | 说明 |
|-------|------|
| xhaip-core | 核心引擎（10 模块 + 14 Agent） |
| xhaip-pharmacy | 药剂科（TPN / 处方审查） |
| xhaip-orthopedic | 骨外科（时机评估 / 风险评估） |
| xhaip-cardio | 心血管外科 + 风险（抗凝 / 心脏评估） |
| xhaip-anesthesia | 麻醉风险（ASA / 气道 / 抗凝） |
| xhaip-pain | 疼痛中心（急慢性疼痛 / 5 子 Agent） |
| xhaip-pediatrics | 儿科（IMCI / 生长发育） |
| xhaip-masterdata | 主数据（病历 / 指标） |

### MCP 服务器

将 Agent 工具暴露为 MCP 协议端点，供外部 AI 客户端（Claude Desktop 等）调用。

```bash
xhaip tools mcp-serve --agent pharmacy --port 8701     # 单 Agent
xhaip tools mcp-serve --all --port 8700                # 所有工具
xhaip tools list                                        # 列出所有工具
xhaip tools list --agent pharmacy                       # 列出 Agent 工具
```

**传输协议**: SSE（FastMCP，推荐）/ JSON-RPC HTTP（内置备选）
**依赖**: `pip install mcp`（可选 — 未安装时自动回退到内置 JSON-RPC 服务器）

## 质量门禁

```bash
ruff check .                               # 代码风格 (2026-07-18 起全仓 ruff 清零, 扩大至全仓)
mypy packages/haip-core/haip/             # 类型检查
pytest --cov=haip --cov-fail-under=70     # 单元测试 + 覆盖率
python scripts/validate_patients.py       # 患者数据质量 (0 FAIL 阻断)
```

### UI 页面契约 (2026-07-17 起强制)

- 新增/修改 HTML 页面必须通过 `pytest tests/test_ui_contracts.py` (C1-C7: DOM id / onclick / PATIENTS / AGENT / fetch 路由 / workflow tool 契约)
- 新增/修改 Agent YAML 或 handler 必须通过 `pytest tests/test_handler_contracts.py` (309+ handler 模块可导入且函数存在)
- 数字病人加载必须走 `haip.patients.load_patients()`, 禁止各 UI 自行解析 patients.json
- 渲染函数禁止在循环中复用函数参数名 (ruff PLR1704 强制)
- 测试环境统一由 `tests/conftest.py` 与 `packages/haip-core/tests/conftest.py` 提供 (`HAIP_TEST_MODE`), 测试文件不再各自设 env
- 修复验证必须复现用户完整操作路径 (选患者 → 执行工具 → Guard → 结果据实), 禁止仅用手工构造输入做点验证

## 患者数据

所有患者记录含 `provenance` 字段（`source` / `origin_repo` / `institution`）。修改患者数据后需运行 `python scripts/validate_patients.py`。

## 与 v0.2.0 的关键差异

| 场景 | v0.2.0 做法 | v1.0 做法 |
|------|-----------|----------|
| 新增 Agent | 创建 Python 子包 + 写 620 行胶水代码 + 改 3 个引擎文件 | 写 30 行 YAML + 写纯业务逻辑 |
| A2A 路由 | 手动改 `A2A_AGENTS` 字典 | 自动从 YAML 的 `handler` 字段生成 |
| LLM 切换 | 改 `llm.py` + `agent_loop.py` + `guard.py` 等 4+ 文件 | 改 1 行配置 `config/llm.yaml` |
| 测试 LLM | 需要真实 API key | MockProvider 返回 fixture，CI 可跑 |
| 编排执行 | `for node in dag.nodes` 顺序 | `toposort_layers()` 分层并行 |
