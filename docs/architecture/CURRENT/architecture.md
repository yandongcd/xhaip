# xhaip Architecture [CURRENT]

> 描述 xhaip v1.0 当前真实架构。融合 haip-0710 遗留的通用设计概念。

## 核心架构

xhaip 是一个 **YAML 驱动的多 Agent 医院 AI 平台**，基于以下 4 个核心原则：

1. **YAML 驱动 Agent**: 新增 Agent 仅需 30 行 YAML + 纯业务逻辑，无需修改引擎代码
2. **引擎独立包**: `haip-core` 为 pip installable 包，跨医院复用
3. **LLM Provider 抽象**: 通过 `LLMProvider` ABC 切换模型，CI 环境可用 MockProvider
4. **知识库 SQLite**: YAML 保持版本化（Source of Truth），运行时 SQLite 毫秒级查询

## 系统分层

```
haip-core (引擎)          haip-hospital (业务)
┌─────────────┐          ┌──────────────────┐
│ agent/       │ ◄────── │ agents/definitions/│ YAML 定义
│ a2a/         │ ◄────── │ modules/          │ Handler 模块
│ llm/         │          │ knowledge/        │ 知识资产
│ tools/       │          │ data/             │ 患者数据
│ guard/       │          └──────────────────┘
│ orchestrator/│
│ knowledge/   │
│ loop/        │
│ togaf/       │
└─────────────┘
```

## Agent 类型体系

| 类型 | 职责 | 数据主权 | 示例 |
|------|------|---------|------|
| **business** | 科室诊疗决策 | 本科室 | orthopedic-surgery, cardiology |
| **specialist** | 跨科室专项评估 | 专项数据 | cardio-risk, anesthesia-risk |
| **master_data** | 全院共享主数据 | 全院 | medical-record, metrics |
| **architecture** | 架构治理 | 全平台 | togaf |

## 五层 Agent Loop 模型

源自 haip-0710 V4.0 设计，xhaip 部分实现：

| 层 | 名称 | xhaip 实现 | 说明 |
|----|------|-----------|------|
| L4 | Inner Loop (ReAct) | `loop/react_loop.py` | LLM 推理 + 工具调用循环 |
| L3 | Guard Loop | `guard/` | 4 层安全验证 (Self-Correction → Citation → Confidence → Cross-Validation) |
| L2 | HITL | **未实现** | 人类决策介入 |
| L1 | Orchestration | `orchestrator/` | TaskDAG + toposort 分层并行 |
| L0 | Learning Loop | **未实现** | 持续学习 |

## T1/T2 信任体系

源自 haip-0710，xhaip 通过 `knowledge/guidelines/` 的 `trust_level` 字段实现：

| 级别 | 含义 | 置信度 | 可变性 |
|------|------|--------|--------|
| T1 | 外部权威来源 (国标/国际指南) | 1.0 | 不可变 |
| T2 | 医院临床适配 | 0.6-0.8 | 可覆盖 |

## Guard 安全验证公式

源自 haip-0710，xhaip `guard/` 模块实现：

```
confidence = source_quality(0.35) + tool_reliability(0.25) + llm_certainty(0.25) + cross_validation(0.15)
```

阈值: ≥0.6 通过 | <0.6 标记 | <0.3 阻断

## 混合分诊路由

源自 haip-0710 设计，xhaip **未实现**但设计文档已就绪:

```
请求 → 规则通道 (0 token, keyword match) → 命中 → 直接返回
         ↓ 未命中
       LLM → Tool → LLM → 结果
```

优先级: P0 (低复杂度) | 价值: 高频简单问题零 token 消耗 | 详见 `DESIGN/design-decisions.md` #DESIGN-001

## A2A Transport 抽象

源自 haip-0710 orchestrator 设计，当前 xhaip A2A 仅支持 InProcess importlib dispatch。
未来应扩展为 4 种 transport: InProcess / MCP / Fallback / Mock

优先级: P1 | 详见 `DESIGN/design-decisions.md` #DESIGN-002

## Agent 版本契约

源自 haip-0710 正式版本规范。当前 xhaip YAML definition 缺少 `version` / `compatibility` / `changelog` 字段。
52 Agent 的版本追踪和破坏性变更检测需要这些元数据。

优先级: P0 (低复杂度) | 详见 `DESIGN/design-decisions.md` #DESIGN-003

## Data Product 适配器

源自 haip-0710 permission-system 的 Adapter 模式。Agent 不直接访问 HIS/EMR，通过 DataProduct(adapter_class) 解耦。
当前 xhaip 未实现。

优先级: P2 | 详见 `DESIGN/permission-system.md`

## 版本

xhaip v1.1 — 融合 haip-0710 设计精华，YAML 驱动重构。含 6 个未来引擎设计蓝图 (DESIGN-001 ~ DESIGN-006)
