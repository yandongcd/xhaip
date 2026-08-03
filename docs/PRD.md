# xhaip — Hospital AI Platform PRD

> **Product Requirements Document — Complete Specification**  
> 从 v1.2 系统逆向提炼 | 可独立构建 | 2026-07-12

---

## 1. 产品概述

xhaip 是一个 **YAML 驱动的多 Agent 医院智能体平台**，覆盖 33+ 临床科室，为医院提供 AI 辅助诊疗决策、临床路径管理、知识库查询和安全合规保障。

### 1.1 产品定位

| 维度 | 说明 |
|------|------|
| 产品类型 | 医院 AI 智能体平台（决策支持系统） |
| 部署模式 | 私有化部署 (on-premise) + Docker Compose |
| 技术栈 | Python 3.10+, FastAPI, SQLite, YAML, Docker |
| 目标用户 | 临床医师、药师、麻醉师、护士、科主任、医院管理层 |
| 核心价值 | 2 小时新增一个科室 Agent（传统方式需 2 天） |

### 1.2 产品愿景

每个临床科室拥有专属 AI 助手，知识与决策标准化、可追溯、安全可控。

---

## 2. 用户画像与场景

### 2.1 核心用户角色

| 角色 | 职责 | 典型场景 | 权限级别 |
|------|------|---------|---------|
| 临床医师 (attending) | 科室诊疗决策 | 术前评估、手术方案、并发症预测 | 本科室 Agent 全部权限 |
| 专科医师 (specialist) | 跨科室专项评估 | 心脏风险评估、麻醉 ASA 分级 | 专项 Agent + 患者数据读 |
| 临床药师 (pharmacist) | 处方审查、TPN 配比 | NRS2002 营养筛查、TPN 计算 | 药剂科全部 + 患者数据读 |
| 护士 (nurse) | 护理执行 | 护理计划生成、生命体征监测 | 患者数据读 + 护理工具 |
| 科主任 (dept_head) | 科室质量管理 | 质控指标监控、架构审计 | 科室全部 + 审计查看 |
| 管理员 (admin) | 系统运维 | Agent 注册、配置管理、权限管理 | 全部权限 |

### 2.2 典型临床场景

| 场景 | Agent | 路径 |
|------|-------|------|
| 老年髋部骨折急诊 | orthopedic-surgery → cardio-risk → anesthesia-risk | 分诊 → 心脏评估 → 麻醉评估 → 手术方案 |
| 肠内肠外营养支持 | pharmacy | NRS2002 筛查 → TPN 配比计算 → 处方审查 |
| 术后恶心呕吐预防 | antiemetic | 术前风险评分 → 药物预防 → 术中决策 → 术后救援 |
| 围术期安全评估 | cardio-risk + anesthesia-risk | RCRI 评分 + ECG 判读 + ASA 分级 |
| 多学科会诊 | orthopedic-surgery + cardio-risk + anesthesia-risk | MDT 纪要生成 + 分歧检测 |

---

## 3. 功能需求 (Functional Requirements)

### FR1: Agent 体系

#### FR1.1 YAML 驱动的 Agent 定义

```
FR1.1.1: 系统必须支持通过单个 YAML 文件定义 Agent
FR1.1.2: YAML 必须包含: name, cn_name, type, port, prompt, tools, guard
FR1.1.3: 系统必须在 YAML 加载后自动完成 A2A 路由、端口分配、工具注册
FR1.1.4: 新增 Agent 不得要求修改任何引擎文件
FR1.1.5: Agent 支持五种类型: business, specialist, master_data, rules, architecture
```

#### FR1.2 Agent 间通信 (A2A)

```
FR1.2.1: 系统必须支持 Agent 间进程内调用 (importlib dispatch)
FR1.2.2: 系统必须支持 MCP/HTTP 远程 Agent 调用
FR1.2.3: 系统必须支持 Mock Transport 用于测试
FR1.2.4: A2A 调用必须记录调用历史 (agent, tool, status, elapsed_ms)
FR1.2.5: 系统必须支持并发批量调用 (call_batch with ThreadPoolExecutor)
```

#### FR1.3 Agent Loop 推理

```
FR1.3.1: 系统必须实现 ReAct 推理循环 (LLM → Tool → LLM 迭代)
FR1.3.2: 系统必须支持 temperature 退火策略
FR1.3.3: 系统必须支持 token 预算控制
FR1.3.4: 系统必须支持工具结果摘要化 (500 字符截断)
FR1.3.5: 系统必须支持 Pre-LLM 关键词路由 (0 token 快速通道)
FR1.3.6: 系统必须支持事件驱动的异步 AgentLoop (AsyncAgentLoop)
```

### FR2: 安全与合规

#### FR2.1 Guard 安全验证

```
FR2.1.1: 系统必须实现 4 层安全验证管道: Citation → Confidence → LLM Self-Correction → Cross-Validation
FR2.1.2: 高危场景 (手术决策/药物交互/心梗评估/麻醉评估/MDT分歧) 必须强制执行完整检查
FR2.1.3: 非高危场景必须至少执行引用验证
FR2.1.4: 置信度 < 0.3 必须硬阻断 (返回 status: blocked)
FR2.1.5: 0.3 ≤ 置信度 < 0.6 必须软标记 (WARNING + flag)
FR2.1.6: 置信度公式: confidence = source_quality(0.35) + tool_reliability(0.25) + llm_certainty(0.25) + cross_validation(0.15)
```

#### FR2.2 引文强制

```
FR2.2.1: Agent 必须可在 YAML 中配置引文策略: guard.citation.{required, min_sources, min_trust}
FR2.2.2: 系统必须支持最小引用数量: guard.citation.min_sources (默认 1)
FR2.2.3: 系统必须支持最低信任级别: guard.citation.min_trust (T1/T2)
FR2.2.4: 不满足引文策略的输出必须被阻断
FR2.2.5: 系统必须自动提取 Agent 输出中的引用标记: `[ref: xxx]`, `参考: xxx`, `依据xxx指南`, `根据xxx标准`
FR2.2.6: 系统必须验证引用是否在指南资产库中存在
```

#### FR2.3 T1/T2 信任体系

```
FR2.3.1: 指南必须标注 trust_level (T1/T2)
FR2.3.2: T1 来源置信度 = 1.0, T2 = 0.6-0.8
FR2.3.3: 高危场景若无 T1 引用，必须标记警告
FR2.3.4: T2 覆盖必须记录到审计日志
```

### FR3: 权限系统

```
FR3.1: U2A — 用户→Agent: 基于角色 (RBAC), JWT token, user_role 多对多, role_agent 多对多
FR3.2: A2A — Agent→Agent: 调用策略表, 通配符支持, 工具级白名单
FR3.3: A2D — Agent→Data: 数据产品策略, dept_scope (self/all/consulted), field_filter
FR3.4: Emergency break-glass: is_emergency 标记绕过全部权限检查
```

### FR4: 审计日志

```
FR4.1: 每次 A2A 调用必须记录 (subject, action, resource, decision, reason)
FR4.2: 权限拒绝 + 策略变更必须记录
FR4.3: append-only 不可篡改
FR4.4: 支持查询: 按 user/action/resource/status/time
```

### FR5: 知识库

```
FR5.1: YAML 为 Source of Truth, 运行时同步到 SQLite
FR5.2: 指南表 9 字段, 规则表 10 字段
FR5.3: 3 索引: idx_rules_set, idx_rules_decision, idx_guidelines_trust
FR5.4: 30s polling 热重载
FR5.5: 指南库覆盖 33+ 科室 (CMA 中华医学会系列 + 国际指南)
```

### FR6: LLM Provider 抽象

```
FR6.1: LLMProvider ABC: chat(messages, tools, temperature, max_tokens) → ChatResponse
FR6.2: chat_stream → Iterator[ChatResponse]
FR6.3: from_config(config_dict) 工厂方法
FR6.4: DeepSeekProvider (生产) + MockProvider (CI)
FR6.5: 切换模型改 config/llm.yaml 一行
```

### FR7: 编排与路由

```
FR7.1: TaskDAG 拓扑排序并行执行 (入度计算 → 分层 → ThreadPoolExecutor)
FR7.2: 三模式: AUTO (LLM 规划), PIPELINE (预定义链), DIRECT (单 Agent)
FR7.3: Pre-LLM 关键词路由: before_agent hook, 匹配即跳过 LLM
FR7.4: ClinicalWorkflow DSL: AGENT/FUNCTION/JOIN/START/END 节点, 条件路由, fan-out/fan-in
```

### FR8: HITL 人工介入

```
FR8.1: 置信度 < 0.3 或 Guard blocked → 生成 HITLRequest
FR8.2: HITLRequest 字段: agent_name, query, proposed_output, guard_flags, confidence, action_required
FR8.3: 状态机: pending → confirmed | rejected
FR8.4: after_agent hook 位置触发
```

### FR9: 数据产品适配器

```
FR9.1: DataSourceAdapter ABC: connect() → query(params: dict) → list[dict] → schema() → dict
FR9.2: SQLiteDataSource (dev), MockDataSource (CI)
FR9.3: DataProduct: name, description, security_label, owner_department, adapter, field_schema
FR9.4: 预注册 11 标准产品 (HIS/LIS/PACS/EMR/NIS 各 2-3 产品)
```

### FR10: 患者数据管理

```
FR10.1: provenance 字段: {source, origin_repo, institution, deidentified, generation_date}
FR10.2: labs 数组格式: [{code, name, value, unit, ref_range, flag}]
FR10.3: validate_patients.py 自动校验
```

### FR11: 部署与运维

```
FR11.1: Docker Compose 7 profile 部署 (core/surgical/medical/emergency/women-children/specialty/pain/arch)
FR11.2: haip-core 独立 pip 包
FR11.3: CLI: xhaip list/info/call/load + sync-skills + release + togaf + tools
FR11.4: Release 备份/回滚 + Audit snapshot/diff/log
FR11.5: TOGAF 治理: 10 实体类型 + 13 关系类型 + 6 CHK 校验 + 4A 构建器
```

---

## 4. 非功能需求 (Non-Functional Requirements)

### NFR1: 性能

```
NFR1.1: Agent 响应时间 < 30s (工具调用在 3 步以内)
NFR1.2: 知识库查询 < 10ms (SQLite indexed)
NFR1.3: A2A 进程内调用 < 5ms (importlib cache)
NFR1.4: 并发批量调用支持 ThreadPoolExecutor (max_workers=8)
```

### NFR2: 可用性

```
NFR2.1: CLI 支持所有管理操作
NFR2.2: Web 门户支持 agent 交互、TOGAF dashboard、workflow 可视化
NFR2.3: 新增 Agent 耗时 ≤ 2 小时 (YAML + handler)
```

### NFR3: 安全

```
NFR3.1: 所有 Agent 调用必须经过权限检查
NFR3.2: 所有用户操作可追溯 (audit log)
NFR3.3: API 密钥通过 .env 管理
NFR3.4: 患者数据脱敏
NFR3.5: 高危决策必须 Guard 验证
```

### NFR4: 可维护性

```
NFR4.1: 引擎/业务完全分离 (packages/haip-core vs haip-hospital)
NFR4.2: 单元测试覆盖率 ≥ 70% (core ≥ 90%)
NFR4.3: YAML 为唯一事实来源
NFR4.4: ruff line-length=100, mypy
```

### NFR5: 可扩展性

```
NFR5.1: Agent 通过 YAML 扩展 (不修改引擎)
NFR5.2: Transport 通过 ABC 扩展
NFR5.3: Data Source 通过 Adapter 扩展
NFR5.4: Guard 规则通过 YAML 配置
```

### NFR6: 合规性

```
NFR6.1: AI 输出可追溯到输入数据和指南来源 (Citation 强制)
NFR6.2: 所有临床决策经过安全验证 (Guard)
NFR6.3: 权限覆盖用户→Agent→数据全链路
NFR6.4: 审计日志包含决策依据 (decision + reason)
```

---

## 5. 架构约束

### 5.1 技术栈约束

| 组件 | 技术 | 原因 |
|------|------|------|
| 语言 | Python 3.10+ | 医院 IT 生态主流 |
| Web 框架 | FastAPI | 自动 OpenAPI docs, 异步支持 |
| CLI 框架 | Typer + Rich | 开发体验 |
| 数据校验 | Pydantic v2 | 类型安全 |
| 配置格式 | YAML | 人类可读写, 版本控制友好 |
| 知识存储 | SQLite | 零配置, 嵌入式, 毫秒查询 |
| LLM Provider | DeepSeek (可切换) | 成本/性能平衡 |
| 容器化 | Docker Compose | 私有化部署标准 |
| 测试框架 | pytest + pytest-cov | 行业标准 |
| Lint | ruff + mypy | 快速, Python 原生 |

### 5.2 架构原则

1. **引擎独立**: haip-core 可跨医院复用，不耦合任何医院特定逻辑
2. **YAML 驱动**: 所有声明式配置用 YAML (Agent/指南/规则/路由)
3. **Provider 抽象**: LLM/Transport/DataSource 都通过 ABC 解耦
4. **SQLite 加速**: YAML 保持版本化, SQLite 提供运行时查询性能
5. **分层安全**: Guard (内容安全) + Permission (访问安全) + Audit (操作审计)

---

## 6. 数据契约 (Data Contracts)

> 本章定义所有持久化层的精确结构。任何字段名、类型、约束的偏离都将导致系统行为变化。

### 6.1 Agent YAML Schema

```yaml
# agents/definitions/{agent-name}.yaml
name: cardiology                    # 必须: 唯一标识 (kebab-case)
cn_name: 心血管内科                  # 必须: 中文名
version: "1.0.0"                    # semver
type: business                      # business | specialist | master_data | rules | architecture
department: 心血管内科               # 科室名
port: 8700                          # 端口
aliases: [心脏科, 心内科]            # 别名列表
depends_on:                         # 版本依赖
  - agent: cardio-risk
    version: ">=1.0"
sub_agents: []                      # 子 Agent
parent: ""                          # 父 Agent
prompt:
  system: |                         # LLM system prompt
    你是一个心血管内科 AI 助手...
  temperature: 0.3
  max_tokens: 4096
tools:                              # 工具列表
  - name: assess_cardiac
    description: 评估心脏风险
    handler: cardiology.assess      # module.function 格式
    input:                          # 参数声明
      symptoms: str
      labs: dict
    output:
      risk_level: str
guard:                              # 安全配置
  triggers: [药物交互, 手术决策]
  high_risk_scenarios: [围术期心肌梗死]
  citation:                         # v1.2 新增
    required: true
    min_sources: 1
    min_trust: T2                   # T1 | T2
ui:                                 # 可选: Web UI 配置
  template: chat-with-role-switcher
  roles:
    - {id: attending, label: 主治医师, default: true}
stages:                             # 可选: 诊疗阶段 (覆盖默认)
  - {order: 1, id: reg, label: 登记与初评}
```

### 6.2 DomainPlugin Dataclass (16 字段)

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | str | — | 唯一标识 (kebab-case) |
| cn_name | str | "" | 中文名 |
| version | str | "1.0.0" | semver |
| type | AgentType | "business" | business/specialist/master_data/rules/architecture |
| department | str | "" | 所属科室 |
| port | int | 0 | 服务端口 |
| aliases | list[str] | [] | 别名 |
| prompt | PromptConfig | PromptConfig() | system prompt + temperature + max_tokens |
| tools | list[ToolDef] | [] | 工具定义列表 |
| depends_on | list[dict] | [] | 版本依赖 |
| sub_agents | list[str] | [] | 子 Agent |
| parent | str | "" | 父 Agent |
| guard | GuardConfig | GuardConfig() | 安全配置 |
| ui | UIConfig | UIConfig() | UI 配置 |
| stages | list[dict] | [] | 诊疗阶段 (覆盖默认) |

### 6.3 GuardConfig 子结构

| 组件 | 字段 | 类型 | 默认值 |
|------|------|------|--------|
| GuardConfig | triggers | list[str] | [] |
| GuardConfig | high_risk_scenarios | list[str] | [] |
| GuardConfig | citation | CitationConfig | CitationConfig() |
| CitationConfig | required | bool | False |
| CitationConfig | min_sources | int | 1 |
| CitationConfig | min_trust | str | "T2" |

### 6.4 Knowledge Store DDL (SQLite)

```sql
-- 指南表
CREATE TABLE guidelines (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    abbr        TEXT,
    publisher   TEXT,
    version     TEXT,
    trust_level TEXT,          -- 'T1' | 'T2'
    language    TEXT,
    source_file TEXT,          -- 源 YAML 文件路径
    key_sections TEXT          -- JSON: 关键章节列表
);
CREATE INDEX idx_guidelines_trust ON guidelines(trust_level);

-- 规则表
CREATE TABLE rules (
    id               TEXT PRIMARY KEY,
    rule_set_id      TEXT,          -- 规则组 ID
    decision_point   TEXT,          -- 决策点
    condition_expr   TEXT,          -- 条件表达式
    conclusion       TEXT,          -- 结论
    rule_type        TEXT,          -- deterministic
    certainty        TEXT,          -- 确定性
    evidence_sources TEXT,          -- JSON: 证据来源列表
    exceptions       TEXT,          -- JSON: 例外规则列表
    priority         INTEGER
);
CREATE INDEX idx_rules_set ON rules(rule_set_id);
CREATE INDEX idx_rules_decision ON rules(decision_point);
```

### 6.5 Permission DDL (SQLite)

```sql
-- 认证表 (8 表)
CREATE TABLE auth_user (
    user_id TEXT PRIMARY KEY, username TEXT, real_name TEXT,
    title TEXT, license_no TEXT, email TEXT, status TEXT DEFAULT 'active'
);
CREATE TABLE auth_role (
    role_code TEXT PRIMARY KEY, role_name TEXT, role_category TEXT
);
CREATE TABLE auth_user_role (
    user_id TEXT, role_code TEXT, PRIMARY KEY (user_id, role_code)
);
CREATE TABLE auth_agent (
    agent_id TEXT PRIMARY KEY, agent_name TEXT, agent_type TEXT,
    department_code TEXT, status TEXT DEFAULT 'active'
);
CREATE TABLE auth_role_agent (
    role_code TEXT, agent_id TEXT, PRIMARY KEY (role_code, agent_id)
);

-- 权限表
CREATE TABLE perm_agent_call_policy (
    id INTEGER PRIMARY KEY, caller_agent_type TEXT, caller_agent_id TEXT,
    target_agent_id TEXT, allowed_tools TEXT, condition TEXT, priority INTEGER
);
CREATE TABLE perm_data_policy (
    id INTEGER PRIMARY KEY, agent_id TEXT, agent_type TEXT,
    data_product TEXT, action TEXT DEFAULT 'read',
    field_filter TEXT, field_denylist TEXT,
    dept_scope TEXT DEFAULT 'self',
    security_label TEXT DEFAULT 'NORMAL',
    requires_consent INTEGER DEFAULT 0
);

-- 审计表
CREATE TABLE audit_access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time TEXT DEFAULT (datetime('now')),
    subject_type TEXT, subject_id TEXT,
    action TEXT, resource_type TEXT, resource_id TEXT,
    decision TEXT, reason TEXT, metadata TEXT
);
```

### 6.6 Seed Data

预置角色: ROLE_PHYSICIAN, ROLE_SPECIALIST, ROLE_PHARMACIST, ROLE_NURSE, ROLE_ANESTHESIOLOGIST, ROLE_EMERGENCY, ROLE_ADMIN

A2A 默认策略: medical-record, metrics, togaf — 所有 Agent 类型可调用 (allowed_tools='*')

---

## 7. API 规范 (API Specifications)

> 本章定义核心模块的精确函数签名、参数类型和返回结构。实现者必须严格遵守以下契约。

### 7.1 a2a.call() — A2A Dispatcher

```python
def call(
    agent: str,              # 目标 Agent 名
    tool: str,               # 工具名
    params: dict[str, Any] | None = None,   # 工具参数
    workflow_id: str = "",                   # 工作流 ID
    caller_agent: str = "",                  # v1.2: 调用方 Agent (版本校验)
    perm_ctx: PermissionContext | None = None, # v1.2: 权限上下文
) -> dict[str, Any]:
    """
    返回:
      {"status": "ok", "reply": "...", ...}       — 成功
      {"status": "error", "error": "...", "code": "..."} — 失败
      {"status": "blocked", "guard": {...}, ...} — Guard 阻断
      {"status": "error", "code": "VERSION_MISMATCH"}     — 版本不匹配
      {"status": "error", "code": "PERMISSION_DENIED"}    — 权限拒绝
    """
```

辅助函数:
- `call_batch(agents: list[str], tool: str, params: dict) → list[dict]` — 并发调用 (ThreadPoolExecutor max_workers=8)
- `call_with_loop(agent: str, query: str, max_steps: int=5) → dict` — ReAct loop 调用
- `_check_version(requirement: str, actual: str) → bool` — semver 校验 (>=1.0, ==1.0)
- `_validate_depends(caller: str, target: str) → str` — 返回 "" 表示通过, 否则返回错误描述

### 7.2 AgentLoop.run() — 推理循环

```python
class AgentLoop:
    def __init__(
        self,
        llm: LLMProvider,
        system_prompt: str,
        tool_executor: Callable[[str, dict], Any] | None,
        tools: list[dict] | None,
        max_steps: int = 5,
        temperature_schedule: tuple[float, ...] = (0.3, 0.4, 0.5, 0.6, 0.7),
        max_tokens: int = 4096,
        max_total_tokens: int = 32000,
        agent_name: str = "default",
        enable_guard: bool = False,            # v1.2
        guard_high_risk_triggers: list[str] | None = None,  # v1.2
    ):
    def run(self, query: str) -> LoopResult:
        """
        LoopResult 字段:
          reply: str               # 最终回答
          steps: int               # 执行步数
          input_tokens: int
          output_tokens: int
          duration_ms: float
          tool_calls: list[dict]   # [{step, tool, args, success, output}]
          error: str               # 错误信息 (guard_blocked/max_steps_exceeded/token_budget_exceeded)
          partial_summaries: list[str]  # 中间步骤摘要
        """

class AsyncAgentLoop(AgentLoop):
    async def run(self, query: str) -> AsyncIterator[SessionEvent]:
        """事件驱动异步推理。每步 yield SessionEvent (assistant_message/tool_result)。"""
```

### 7.3 GuardVerifier.verify() — 安全验证

```python
class GuardVerifier:
    def __init__(
        self,
        citation_engine: CitationEngine | None = None,
        confidence_scorer: ConfidenceScorer | None = None,
        llm_provider: LLMProvider | None = None,
    ):
    def verify(
        self,
        agent_output: str,                    # Agent 输出文本
        scenario: str = "",                   # 高危场景名
        agent_name: str = "",                 # Agent 名称
        tool_results: list[dict] | None = None,
        cross_agent_outputs: list[str] | None = None,
        llm_temperature: float = 0.3,
    ) -> GuardResult:
        """
        执行流程:
          1. 始终执行 Citation 提取 + 验证
          2. 非高危 → 返回 (仅 citation 检查)
          3. 高危 → 完整 4 层: Citation → Confidence → Self-Correction → Cross-Validation

        GuardResult 字段:
          passed: bool             # 整体通过
          flags: list[str]         # 标记列表
          citations: list[Citation] # 引用列表
          confidence: ConfidenceScore | None
          corrected_output: str    # LLM 修正后输出
          requires_human_review: bool
          cross_validation_conflict: bool
          cross_validation_detail: str
        """
```

### 7.4 CitationEngine — 引文引擎

```python
class CitationEngine:
    # 提取模式 (4 个 regex)
    EXTRACT_PATTERNS = [
        re.compile(r"\[ref:\s*(.+?)\]"),           # [ref: xxx]
        re.compile(r"参考[:：]\s*(.+?)(?:[。\n]|$)"),  # 参考: xxx
        re.compile(r"依据(.+?指南)[，。\n]"),        # 依据xxx指南
        re.compile(r"根据(.+?标准)[，。\n]"),        # 根据xxx标准
    ]

    # T1 信任关键词 (15 个)
    T1_KEYWORDS = [
        "国际", "WHO", "NICE", "AAOS", "ACCP", "AHA", "ACC", "ESC",
        "WS/T", "国家标准", "全国临床检验操作规程", "grade 1", "level 1",
        "KDIGO", "ADA", "ESPEN", "CSPEN", "ASPN", "CSCO",
    ]

    # T2 信任关键词 (8 个)
    T2_KEYWORDS = ["共识", "专家", "院内", "南方医院", "广东省", "科室", "中华医学会"]

    def extract(self, text: str) -> list[Citation]: ...
    def verify(self, citations: list[Citation]) -> list[Citation]: ...
    def has_unverified(citations) -> bool: ...    # static
    def all_t1(citations) -> bool: ...            # static

class Citation:
    claim: str
    source: str
    trust_level: str       # "T1" | "T2"
    verified: bool
    guideline_file: str
    warning: str
```

### 7.5 PermissionManager — 权限管理

```python
class PermissionManager:
    def __init__(self, db_path: str = ":memory:"):
    def seed_defaults(self, agent_ids: list[str] | None = None) -> None:
    def get_user_roles(self, user_id: str) -> list[str]:
    def get_accessible_agents(self, user_id: str) -> list[str]:
    def can_call_agent(self, ctx: PermissionContext, target_agent: str, tool: str = "*") -> bool:
        """3 层检查: A2A policy table → auth/rbac → role fallback"""
    def can_access_data(self, ctx: PermissionContext, data_product: str,
                        patient_department: str = "") -> tuple[bool, list[str] | None]:
    def log_access(self, ctx, action: str, resource: str, decision: str, reason: str = "") -> None:
        """双通道记录: SQLite + auth.AuditLogger bridge"""
    def can(self, role: str, action: str) -> bool:

class PermissionContext:
    user_id: str
    role: str
    agent_id: str
    department: str
    is_emergency: bool
```

### 7.6 其他核心 API

```python
# Transport (a2a/transport.py)
class AgentTransport(ABC):
    def call(self, agent: str, tool: str, params: dict) -> dict: ...

class InProcessTransport(AgentTransport): ...
class MockTransport(AgentTransport):
    def __init__(self, responses: dict[str, dict] | None = None):
    call_log: list[dict]

class MCPTransport(AgentTransport):
    def __init__(self, base_url: str, timeout: float = 30.0):

def set_transport(agent: str, transport: AgentTransport) -> None: ...
def get_transport(agent: str) -> AgentTransport | None: ...

# KeywordRouter (loop/routing.py)
class KeywordRouter:
    def add(self, keyword: str, agent: str, tool: str, priority: int = 0) -> None:
    def add_batch(self, keywords: list[str], agent: str, tool: str, priority: int = 0) -> None:
    def match(self, ctx: HookContext) -> str | None:
        """before_agent hook — 返回 __ROUTE__:agent:tool 则跳过 LLM"""

# HITL (loop/hitl.py)
class HITLHook:
    def __init__(self, required_below: float = 0.3):
    def check(self, ctx: HookContext, reply: str) -> str | None:
        """after_agent hook — 返回 [HITL PENDING] 消息则等待人工"""

class HITLRequest:
    agent_name, query, proposed_output, guard_flags, confidence: float
    action_required: str   # confirm_or_reject | free_text
    status: str            # pending | confirmed | rejected

# Data Product (data/__init__.py)
class DataSourceAdapter(ABC):
    def connect(self) -> None: ...
    def query(self, params: dict) -> list[dict]: ...
    def schema(self) -> dict: ...

class SQLiteDataSource(DataSourceAdapter):
    def __init__(self, db_path: str, table: str, query_template: str = ""):

class MockDataSource(DataSourceAdapter):
    def __init__(self, data: list[dict] | None = None):

class DataProduct:
    name, description, security_label, owner_department: str
    adapter: DataSourceAdapter | None
    field_schema: dict[str, str]

class DataProductRegistry:
    def register(self, product: DataProduct): ...
    def get(self, name: str) -> DataProduct | None: ...
    def list_all(self) -> list[str]: ...
    def list_by_security(self, max_label: str) -> list[DataProduct]: ...
    def seed_defaults(self): ...  # 11 标准产品

# Knowledge Runtime
class KnowledgeRuntime:
    _instance: KnowledgeRuntime | None    # singleton
    _store: KnowledgeStore               # SQLite
    _hot_reload_thread: Thread | None    # 30s polling
    def start_hot_reload(self, interval: float = 30.0): ...
    def stop_hot_reload(self): ...

class CaseManager:
    def load(self, path: Path) -> None:
    def search(self, **filters) -> list[PatientRecord]:
    def stats(self) -> dict:
    def compatible_agents(self, patient_id: str) -> list[str]:
```

---

## 8. 算法规范 (Algorithm Specifications)

> 本章定义系统中最关键的算法。实现者必须完全按照以下逻辑实现。

### 8.1 Guard 安全验证管道

```
输入: agent_output (str), scenario (str), agent_name (str)

Step 1: Citation 提取 (始终执行)
  - 用 4 个 EXTRACT_PATTERNS regex 从 agent_output 提取引用
  - 对每个引用: 用 T1_KEYWORDS/T2_KEYWORDS 推断 trust_level
  - 验证: 模糊匹配引用名与 guidelines_dir 中的文件名

Step 2: 风险判定
  - 遍历 HIGH_RISK_SCENARIOS 的 5 个类别 + 27 个 keywords
  - 检查 scenario + agent_output 是否包含任一 keyword
  - 非高危 → return GuardResult()  (仅 citation 已完成)

Step 3: Confidence 评分 (仅高危)
  - source_quality = (
      >=50% T1 citations     → 1.0
      >=50% verified          → 0.8
      else                    → 0.6
    )
  - tool_reliability = 成功工具调用数 / 总调用数 (无调用 → 0.8)
  - llm_certainty = max(0.4, 1.0 - temperature)
  - cross_validation = 无冲突 → 1.0, 有冲突 → 0.4
  - confidence = source_quality(0.35) + tool_reliability(0.25)
               + llm_certainty(0.25) + cross_validation(0.15)

Step 4: 阻断判定
  - confidence < 0.3  → passed=False, blocked
  - 0.3 ≤ confidence < 0.6 → flagged_for_review, requires_human_review=True

Step 5: LLM 自纠 (可选, 需 llm_provider)
  - prompt: "你是医疗审核专家。审查以下输出，纠正事实错误..."
  - temperature=0.05
  - 修正后文本 != 原文本 → corrected_output

Step 6: 交叉验证 (需 cross_agent_outputs)
  - 检查 9 对冲突词 (高风险/低风险, 高危/安全...)
  - 任一冲突 → cross_validation_conflict=True

输出: GuardResult(passed, flags, citations, confidence, corrected_output, requires_human_review, ...)
```

### 8.2 TaskDAG 拓扑排序并行执行

```
输入: nodes (list[TaskNode])

Step 1: 构建依赖图
  - 为每个 node 建立入度计数: indegree[node.id] = len(node.depends_on)
  - 建立下游映射: dependents[dep] ← node.id

Step 2: 分层 (toposort_layers)
  - layer = [n for n in nodes if indegree[n.id] == 0]  # 无依赖节点
  - 移除 layer 中节点，更新 indegree
  - 重复直到所有节点分层或检测到环路
  - 环路中的节点标记 error

Step 3: 并行执行
  - for each layer:
    - max_workers = min(len(layer), 8)
    - with ThreadPoolExecutor(max_workers):
      - 并行执行 layer 中所有节点
      - 每个节点执行完成后，将其下游节点的 indegree 减 1
    - 若节点 result.status == "error":
      - 跳过其所有下游节点 (skip-on-error)
  - 收集所有节点结果

输出: OrchestrationResult(status, answer, nodes, errors, total_elapsed_ms)
```

### 8.3 引文提取与信任推断

```
extract(text):
  citations = []
  seen_sources = set()
  for pattern in EXTRACT_PATTERNS:
    for match in pattern.finditer(text):
      source = match.group(1).strip()
      if source and source not in seen_sources:
        trust = _guess_trust_level(source)
        citations.append(Citation(source=source, trust_level=trust))

_guess_trust_level(text):
  for kw in T1_KEYWORDS:
    if kw.lower() in text.lower(): return "T1"
  for kw in T2_KEYWORDS:
    if kw.lower() in text.lower(): return "T2"
  return "T2"  # default

verify(citations):
  if not _index:  # 无索引
    c.warning = "no guidelines indexed"
    return
  for c in citations:
    key = c.source.lower().replace(" ", "_").replace("-", "_")
    if key in _index:
      c.verified = True; c.guideline_file = str(_index[key])
    else:
      # Fuzzy: check if any indexed key contains this source or vice versa
      for stem, path in _index.items():
        if stem in key or key in stem:
          c.verified = True; c.guideline_file = str(path); break
    if not c.verified:
      c.warning = "未在指南资产库中找到对应文件"
```

### 8.4 Keyword 路由匹配

```
match(ctx):
  query = ctx.metadata.get("query", "").lower()
  if not query: return None

  matched = []
  for route in routes:
    for kw in route.keywords:
      if kw in query:  # 子串匹配
        matched.append(route); break

  if not matched: return None

  matched.sort(key=lambda r: r.priority, reverse=True)
  best = matched[0]
  return f"__ROUTE__:{best.agent}:{best.tool}"  # HookChain 用此格式跳过 LLM
```

### 8.5 版本依赖校验

```
_check_version(requirement: str, actual: str) → bool:
  _version_tuple(v):
    parts = int(v.split(".")[:3]), pad to 3 with 0
    return tuple(parts)

  if req starts ">=":  return actual_tuple >= target_tuple
  if req starts "==":  return actual_tuple == target_tuple
  if req starts ">" (not ">="):  return actual_tuple > target_tuple
  # bare version: exact
  return actual_tuple == req_tuple
```

---

## 9. 钩子系统 (Hook & Lifecycle)

> 系统使用 ADK 风格的 6 节点钩子系统。钩子通过返回非 None 值跳过/替代默认行为。

### 9.1 Hook Chain 结构

```python
class HookChain:
    before_agent: list[Callable[[HookContext], str | None]]    # return str → skip agent
    after_agent:  list[Callable[[HookContext, str], str | None]]  # modify reply
    before_llm:   list[Callable[[HookContext, list[dict], dict | None], ChatResponse | None]]
    after_llm:    list[Callable[[HookContext, ChatResponse], ChatResponse | None]]
    before_tool:  list[Callable[[HookContext, str, dict], dict | None]]
    after_tool:   list[Callable[[HookContext, str, dict, Any], dict | None]]
```

### 9.2 Hook 生命周期

```
Agent.Run 生命周期:
  before_agent hooks → [若返回 str, 跳过 Agent]
    ├── before_llm hooks → LLM.call → after_llm hooks
    ├── before_tool hooks → Tool.execute → after_tool hooks
  after_agent hooks → return

每个 hook 在 HookContext 中可访问:
  agent_name, invocation_id, session_id, step, metadata: dict
```

### 9.3 已实现的钩子

| 钩子 | 位置 | 类 | 触发条件 |
|------|------|-----|---------|
| 关键词路由 | before_agent | KeywordRouter.match() | 用户 query 匹配路由关键词 |
| HITL 检查 | after_agent | HITLHook.check() | 置信度 < 0.3 或 Guard blocked |
| Guard 验证 | 内置 in loop | GuardVerifier.verify() | enable_guard=True, 每 step 输出后 |

---

## 10. 状态机 (State Machines)

### 10.1 HITL 状态机

```
            ┌─────────┐
            │ pending │  ← Guard blocked 或 confidence < 0.3
            └────┬────┘
           ┌─────┴─────┐
           ▼             ▼
      ┌────────┐   ┌──────────┐
      │confirmed│   │ rejected │
      └────────┘   └──────────┘
         │               │
         ▼               ▼
    继续执行        返回拒绝消息
```

### 10.2 AgentLoop 状态机

```
          ┌──────────────────────────────────────────────┐
          │                                               │
  START → LLM.call ──→ tool_calls? ──yes→ Tool.execute ──┤
              │               │                           │
              └──no──→ final_answer ──→ Guard.verify ──→ END
                                          │
                              ┌─passed──┤
                              │          └─blocked──→ HITL.pending
                              ▼
                            return
```

### 10.3 Guard 门控状态

```
  agent_output
       │
       ▼
  ┌──────────┐   非高危    ┌──────────────┐
  │ Citation │──────────→│ light check  │ → return (passed)
  │ extract  │            │ (unverified?)│
  └────┬─────┘            └──────────────┘
       │ 高危
       ▼
  ┌──────────┐
  │Confidence│
  │ scoring  │
  └────┬─────┘
       │
  ┌────┴────┐──────────────┐
  │ < 0.3   │ 0.3-0.6     │ ≥ 0.6
  ▼         ▼              ▼
BLOCKED   WARN+FLAG      PASS
  │         │              │
  ▼         ▼              ▼
HITL      continue     continue
```

---

## 11. 模块间桥接 (Module Bridges)

> xhaip 采用模块解耦设计，模块间通过桥接 (bridge) 通信，不直接 import。

| 桥接 | 方向 | 方式 |
|------|------|------|
| a2a → guard | a2a.call_with_loop() 调用 GuardVerifier.verify() | 直接 import (engine-level) |
| a2a → permission | a2a.call() 通过 perm_ctx 查询 PermissionManager | 可选依赖 (try/except ImportError) |
| permission → auth/rbac | PermissionManager._role_can_fallback → auth.rbac.has_permission() | 可选依赖 |
| permission → audit | PermissionManager.log_access → audit.AuditLogger.log() | 可选依赖 |
| loop → guard | AgentLoop 内置 GuardVerifier (enable_guard=True) | 直接 import |
| loop → routing | HookChain before_agent → KeywordRouter.match() | Hook 注册 |
| loop → hitl | HookChain after_agent → HITLHook.check() | Hook 注册 |
| knowledge → guard | KnowledgeRuntime.verify_citations → CitationEngine.verify() | 直接 import |
| orchestrator → a2a | A2AOrchestrator 通过 a2a.call() 执行节点 | 直接 import |
| agent → togaf | DomainPlugin 注册时触发 TOGAF 校验 | on_register callback |

---

## 12. 交付里程碑

| 版本 | 核心交付 | 状态 |
|------|---------|------|
| v0.2.0 (haip-0710) | 11 Agent (Python 子包), 5-Layer Loop 设计, 58 Skills | 归档 |
| v1.0 (xhaip) | 52 YAML Agent, monorepo, pip-installable engine, 457 tests | ✅ |
| v1.1 | 两库合一 (8 engine 移植, provenance, GitHub infra, 架构文档) | ✅ |
| v1.2 | PROD-READY (Permission, Guard gating, Citation, Transport, HITL, DataProduct, 681 tests) | ✅ |

---

## 13. 质量门禁

| 门禁 | 标准 | 阻断级别 |
|------|------|---------|
| ruff | 0 errors | 阻断 CI |
| mypy | 0 errors (changed files) | 阻断 PR |
| pytest | 100% pass | 阻断 CI |
| 覆盖率 | ≥ 70% (core ≥ 90%) | 阻断 PR |
| validate_patients.py | 0 FAIL | 阻断 CI |
| Guard gating | passed=True (高危场景) | 阻断响应 |
| Permission | A2A 调用前强制检查 | 阻断调用 |
| Citation | 满足 min_sources + min_trust | 阻断响应 (配置开启时) |
| Version depends | 版本不匹配时阻断 | 阻断调用 |

---

## 14. TOGAF 10 架构治理

> 全平台架构治理子系统，由 20 个模块文件组成。xhaip 的所有 Agent 必须在启动时通过 TOGAF 校验。

### 14.1 实体模型 (Metamodel)

#### 10 种 EntityType (4 层)

| ID | 中文名 | Layer | Description |
|----|--------|-------|-------------|
| Organization | 组织 | Business | 医院/科室/团队 |
| Actor | 行动者 | Business | 医生/护士/药师 |
| Role | 角色 | Business | 主治医师/护士长 |
| BusinessService | 业务服务 | Business | 门诊挂号/处方审核 |
| BusinessProcess | 业务流程 | Business | 骨折分型流程/TPN配置流程 |
| DataEntity | 数据实体 | Data | 患者信息/检验报告/处方 |
| ApplicationComponent | 应用组件 | Application | 骨外科Agent/药剂科Agent |
| ApplicationService | 应用服务 | Application | 心脏风险评估/麻醉评估 |
| TechnologyComponent | 技术组件 | Technology | Python Runtime/SQLite |
| TechnologyService | 技术服务 | Technology | REST API/数据库查询 |

#### Agent Type → EntityType 映射

| agent.type | TOGAF EntityType |
|------------|-----------------|
| business | ApplicationComponent |
| specialist | ApplicationService |
| master_data | DataEntity |
| rules | BusinessService |
| architecture | ApplicationComponent |

#### 13 种 RelationshipType (4 类)

| 类别 | ID | Source → Target | 说明 |
|------|-----|----------------|------|
| Composition | has, employs, contains, composed_of | Organization/Actor/DataEntity 之间 | 层级包含 |
| Assignment | plays, participates_in, executes | Actor→Role, AppComp→BP | 角色/执行 |
| Realization | supports, stores, runs_on, deployed_on | App→Business/Data/Tech | 支撑/部署 |
| Interaction | communicates_via, accesses | AppComp→AppComp, App→Data | 通信/访问 |

### 14.2 组织架构 (Organization)

- **71 节点，8 类**: leadership(7) + admin(27) + clinical(34) + medical_tech(8) + research(11) + education(4) + branch(4) + cross-department(2)
- **184 角色**，14 级: 院领导→科主任→主治医师→住院医师→护士长→责任制护士→麻醉医师→临床药师→医技主任→技师→科研PI→研究员→教学主任→教师
- 每角色含 10 个 focus areas
- 核心 API: `build_org_tree()`, `list_orgs()`, `list_roles()`, `get_role()`, `get_org()`

### 14.3 6 CHK 校验器

| ID | Name | 检查什么 |
|----|------|---------|
| CHK-001 | Type Compliance | agent.type 映射到合法的 TOGAF EntityType |
| CHK-002 | Org Affiliation | agent.department 存在于组织树 |
| CHK-003 | Role Validity | agent.ui.roles 属于科室的有效角色 |
| CHK-004 | Dependency Graph | depends_on 中的 Agent 已注册且可达 |
| CHK-005 | Tool→Service Mapping | handler 格式 module.function，覆盖率 ≥70% |
| CHK-006 | Principles Compliance | 遵循 TOGAF 原则 (domain-as-plugin, tool-as-contract, no-duplication, no-hardcode) |

### 14.4 4A 构建器

```python
class Architecture4A:
    domain: str
    value_streams: list[ArchitectureNode]       # BA
    business_processes: list[ArchitectureNode]  # BA
    business_services: list[ArchitectureNode]   # BA
    data_entities: list[ArchitectureNode]       # DA
    application_components: list[ArchitectureNode]  # AA
    application_services: list[ArchitectureNode]    # AA
    technology_components: list[ArchitectureNode]   # TA
    technology_services: list[ArchitectureNode]     # TA
    edges: list[ArchitectureEdge]
    def nodes() → list[Node]: ...
    def summary() → str: ...
```

目前注册域: orthopedic (5 value streams, 10 BPs, 7 data entities, 4 app components, 5 tech components)

### 14.5 其他模块

- **audit.py**: `auto_discover()` — 自动发现部署环境, 导出 ArchitectureLandscape
- **governance.py**: BP 校验, BPCheckResult, BPValidationReport
- **roles.py**: 5 临床视角 (主治医师/住院医师/药师/麻醉师/护士长) 对骨科病人做不同呈现
- **templates.py**: 渲染 TOGAF 模板 (list/report/catalog), TEMPLATE_MANIFEST
- **dashboard.py**: 成熟度热力图 + 元模型可视化
- **agent_generator.py**: 从 TOGAF spec 自动生成 Agent YAML
- **patient_generator.py**: TOGAF 数据实体驱动的患者生成

---

## 15. ClinicalWorkflow DSL

> 声明式临床工作流定义语言。支持扇入/扇出、条件路由、并行执行。

### 15.1 Node 类型

| NodeType | Value | 说明 |
|----------|-------|------|
| AGENT | "agent" | LLM Agent 节点 — 调用 a2a loop |
| FUNCTION | "function" | 纯函数节点 — 确定性代码 |
| JOIN | "join" | 扇入屏障 — 等待全部前驱 |
| START | "start" | 隐式起始节点 (图中不显式定义) |
| END | "end" | 隐式结束节点 (自动推导) |

### 15.2 边定义风格

1. **顺序链**: `("A", "B", "C")` → A→B→C
2. **条件路由**: `(source, {"high": target_a, "low": target_b})` 或 `(source, router, {"high": target_a})`
3. **扇出/扇入**: 多条边指向同一 JoinNode → 自动并行 → barrier 等待

### 15.3 编译 Pipeline

```
edges → _add_sequential() / _add_conditional()
     → 注册 Node + 构建 adjacency + Route 对象
     → toposort_layers() (Kahn 算法: 入度 → 队列 → 分层)
     → 输出 layers: list[list[str]]
```

### 15.4 执行引擎

```
execute(ctx, input_data):
  layers = toposort()
  for each layer:
    asyncio.gather(parallel exec within layer)
    _execute_node:
      FUNCTION → loop.run_in_executor(node.func, data)
      AGENT    → a2a.call(node.agent_name, tool, data)
      JOIN     → pass-through (toposort 已处理 barrier)
    yield Event after each node
```

### 15.5 WorkflowBuilder (Fluent API)

| 方法 | 用途 |
|------|------|
| `add_agent(id, agent_name, label)` | 添加 AGENT 节点 |
| `add_function(id, func, label)` | 添加 FUNCTION 节点 |
| `add_join(id, label)` | 添加 JOIN 节点 |
| `chain(*ids)` | 顺序链 A→B→C |
| `route(source, route_map)` | 条件路由 (自动生成 router 节点) |
| `fan_out(source, *targets)` | 并行扇出 A→B, A→C |
| `fan_in(join_id, *sources)` | 扇入到 join A→J, B→J |
| `build()` → `ClinicalWorkflow` | 编译并返回就绪工作流 |

---

## 16. AsyncAgentLoop 事件协议

### 16.1 Event 完整定义

```python
@dataclass
class Event:
    id: str             # 默认: f"evt_{uuid4().hex[:12]}"
    invocation_id: str  # 每次 Agent 调用唯一 ID
    author: str         # "user" | "assistant" | tool_name
    timestamp: float    # time.time()
    content: str        # 文本内容
    role: str           # "user" | "assistant" | "tool"
    tool_name: str      # 工具名 (仅 tool role)
    tool_args: dict     # 工具参数
    partial: bool       # streaming 部分标记
    state_delta: dict   # key-value 状态变更 (None = delete)
    artifact_delta: dict# 产物变更
    turn_complete: bool # 对话轮次完成标记
    error: str          # 错误信息
    branch: str         # 对话分支名
```

### 16.2 Event 工厂方法

```
Event.user_message(content, invocation_id)
  → role="user", turn_complete=True

Event.assistant_message(content, invocation_id, partial=False, turn_complete=False, state_delta={}, error="")
  → role="assistant"

Event.tool_result(name, content, invocation_id, state_delta={})
  → role="tool"
```

### 16.3 SessionService 接口

```python
class SessionService:
    def create_session(app_name, user_id, state={}, session_id="") → AgentSession
    def get_session(session_id, app_name, user_id) → AgentSession | None
    def list_sessions(app_name, user_id, limit=50) → list[dict]
    def delete_session(session_id) → bool
    def append_event(session, event) → None
    def rewind_session(session, keep_events: int) → None
    def begin_invocation(session) → str
    def end_invocation(session) → None
    def close() → None

class InMemorySessionService:  # 相同接口，无持久化，threading.Lock
```

### 16.4 events_to_messages 转换

```
events → 过滤 role in ("user","assistant","tool")
      → 可选 truncate 到 max_turns 个 user turns
      → 映射:
        user → {"role":"user","content":...}
        assistant → {"role":"assistant","content":...}
        tool → {"role":"tool","tool_call_id":event.id,"content":...}
```

### 16.5 AsyncAgentLoop Streaming 生命周期

```
START → begin_invocation(session)
     → for each step in max_steps:
         LLM.chat(messages, tools, temperature)
         → yield Event.assistant_message(partial=True)
         → if tool_calls:
             Tool.execute → Event.tool_result()
             → messages.append(tool_result)
         → if no tool_calls:
             Guard.verify(output)
             → yield Event.assistant_message(turn_complete=True)
             → break
     → end_invocation(session)
     → END
```

---

## 17. 配置文件精确格式

### 17.1 config/llm.yaml

```yaml
llm:
  provider: deepseek                     # deepseek | openai | mock
  model: deepseek-chat                   # 模型名
  api_key: "${DEEPSEEK_API_KEY}"         # 环境变量引用
  api_base: "https://api.deepseek.com/v1"
  temperature: 0.3
  max_tokens: 4096
  timeout: 30
  retry: 2

fallback:
  provider: mock                         # LLM 不可用时的降级
  mock_responses: true
```

LLMProvider.from_config() 解析逻辑:
1. 读 `llm.provider` → 决定具体 Provider 类
2. 读 `llm.model` → 传给 Provider
3. 读 `llm.api_key` → 支持 `${ENV_VAR}` 替换
4. 读 `llm.api_base` → API 端点
5. 若 Provider 初始化失败 → 降级到 `fallback.provider`

### 17.2 config/haip.yaml

```yaml
server:
  host: "0.0.0.0"
  port: 8769
  reload: false
  workers: 1

auth:
  enabled: true
  jwt_secret_key: "${JWT_SECRET_KEY:xhaip-dev-secret-change-in-production}"
  access_token_expire: 900              # 15 minutes
  refresh_token_expire: 604800          # 7 days
  default_admin_password: "${HAIP_ADMIN_PASSWORD:Admin@123456}"

security:
  cors_origins: ["*"]
  rate_limit_enabled: false
  rate_limit_per_minute: 100
  encryption_key: "${ENCRYPTION_KEY:xhaip-dev-encryption-key-change-me}"

audit:
  enabled: true
  max_events: 100000
  log_agent_calls: true
  log_api_calls: true

agents:
  definitions_dir: "packages/haip-hospital/agents/definitions"
  auto_load: true
  validate_on_load: true

knowledge:
  rules_dir: "packages/haip-hospital/knowledge/rules"
  guidelines_dir: "packages/haip-hospital/knowledge/guidelines"
  patients_file: "packages/haip-hospital/data/patients.json"

togaf:
  organization: true
  validation:
    enabled: true
    checks: [CHK-001, CHK-002, CHK-003, CHK-004, CHK-005, CHK-006]
  governance:
    bp_validation: true
    guideline_check: true
  dashboard:
    enabled: true
```
