# 设计决策记录 [DESIGN]

> 源自 haip-0710 `design-thinking-faq.md` (30 条 Q&A) + xhaip ADR  
> 状态: [未实现] — 蓝图，为未来引擎升级提供参考

## ADR-001: TOGAF 10 作为架构基础

**决策**: 采用 TOGAF 10 作为 xhaip 的架构治理框架。
**理由**: 10 种实体类型 + 13 种关系类型提供标准化的医院架构建模能力。
**实现**: `packages/haip-core/haip/togaf/` (16 模块)
**来源**: xhaip `docs/adr/ADR-001-*.md`

## ADR-005: 止吐药 Agent 迁移

**决策**: 将 `druganalysis` Agent 从旧架构迁移到 xhaip YAML 驱动模式。
**实现**: `agents/definitions/antiemetic.yaml` + `modules/antiemetic/`
**来源**: xhaip `docs/adr/ADR-005-*.md`

## DESIGN-001: 混合分诊引擎

**设计**: 两条路径 — 规则通道 (0 token, keyword match) > 未命中 → LLM 通道
**价值**: 高频简单问题零 token 消耗，降本增效
**优先级**: P0 (低复杂度)
**来源**: haip-0710 `architecture.md` §19
**状态**: [DESIGN] 未实现

## DESIGN-002: Transport 抽象

**设计**: A2A Dispatcher 支持 4 种传输模式 — InProcess / MCP / Fallback / Mock
**价值**: CI 可注入 Mock，生产可切换 MCP
**优先级**: P1 (中复杂度)
**状态**: [DESIGN] 未实现

## DESIGN-003: Agent 版本契约

**设计**: YAML definition 增加 `version`、`compatibility`、`changelog` 字段
**价值**: 52 Agent 版本追踪，破坏性变更可检测
**优先级**: P0 (低复杂度)
**状态**: [DESIGN] 未实现

## DESIGN-004: Data Product 适配器

**设计**: Agent → DataProduct(adapter_class) → 数据源。换 adapter 即可接入真实 HIS/EMR
**价值**: 解耦 52 Agent × 医院系统，零代码接入
**优先级**: P2 (中复杂度)
**状态**: [DESIGN] 未实现

## DESIGN-005: T1/T2 信任融合

**设计**: 将 haip-0710 的 T2_OVERRIDE 标注语法 + linter 规则融入 xhaip guard 模块
**价值**: 规则库支持医院级定制，同时追踪变异性
**优先级**: P1 (中复杂度)
**状态**: [DESIGN] 未实现

## DESIGN-006: 双路径规则引擎

**设计**: DSL expression evaluator (90%) + Python callbacks (10%) + Arbitration engine
**价值**: 规则可热更新，减少硬编码
**优先级**: 待重新评估 — xhaip 已选 YAML static + LLM，引入 DSL 可能重复
**状态**: [DESIGN] 待决策

## 30 条设计决策 (0710 原文摘要)

> 以下从 haip-0710 `design-thinking-faq.md` 提炼核心决策

1. Agent 拆分标准: 70% 业务流程差异 → 独立 Agent
2. UI 设计路径: Python HTML 模板 → 后续可迁移 React
3. 规则引擎: DSL 主力 (90%) + Python 回调 (10%)
4. 资产分类: 5 类 (Shared Library / MCP Shared / MCP Skill / Mock / Domain)
5. 命名规范: snake_case 模块, kebab-case agent-name
6. Git 安全: 四层纵深防御 (OpenCode 拦截/validate 检查/AGENTS.md/审计)
7. Chat 规范: 必须通过 Nexent Runtime API (xhaip 已废弃此依赖)
8. Bat 文件: UTF-8 编码, 对应 agent 端口
9. 端口分配: 8765-8843 段
10. MCP 工具: 通过 A2A dispatch 调用, 不直接 import
(其余 20 条见 haip-0710 原文 `docs/architecture/design-thinking-faq.md`)
