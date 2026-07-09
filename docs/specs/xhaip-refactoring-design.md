# xhaip v1.0 重构设计方案

> 平行重建：`xhaip/` 从零构建，老 `haip-0705-2/` 不动，完成后切换。

## 一、四个核心原则

| 原则 | 现状痛点 | 新方案 | 收益 |
|------|---------|--------|------|
| **1. YAML 驱动 Agent** | 每个 Agent 620+ 行胶水代码 + 改 3 文件 | 30 行 YAML + 纯业务逻辑 | 2 天 → 2 小时 |
| **2. 引擎独立包** | 38 文件在业务包内，无法独立测试 | `haip-core` pip 包，独立 CI | 跨医院复用 |
| **3. LLM Provider 抽象** | urllib 直连 DeepSeek | LLMProvider 接口 + from_config() | 改 1 行配置切换模型 |
| **4. 知识库 SQLite** | 48 YAML 文件遍历解析 | 启动时 YAML → SQLite，运行时毫秒查询 | YAML 保持版本化 |

## 二、项目结构

```
D:\FC\xhaip\
├── packages/
│   ├── haip-core/              # 核心引擎（pip installable）
│   │   ├── haip/               # agent/ a2a/ orchestrator/ guard/ llm/ loop/ tools/ knowledge/
│   │   └── tests/              # 单元测试 ≥ 80%
│   └── haip-hospital/          # 医院领域实现
│       ├── agents/definitions/ # YAML Agent 定义
│       ├── modules/            # 手写业务逻辑
│       ├── knowledge/          # 指南/规则/角色/组织
│       └── assets/             # UI 模板
├── config/                     # YAML 配置
├── docker/
└── tests/integration/
```

## 三、实施里程碑

| # | 验收标准 |
|---|---------|
| M1 | `haip-core` 骨架 + Mock Provider + 单测 ≥ 80% |
| M2 | YAML loader + registry，药剂科 YAML 可加载注册 |
| M3 | A2A Router + 统一 dispatch，药剂科 calculate_tpn 调通 |
| M4 | Guard Loop + Citation + Confidence，处方审核高危验证 |
| M5 | Orchestrator 并行 DAG，药剂科+病历跨 Agent 调用 |
| M6 | 药剂科全链路 E2E → **第一个里程碑** |
| M7 | 骨科/心外/儿科/心脏评估/麻醉评估/病历/指标迁移 |
| M8 | 疼痛科 6 Agent 迁移，Hub+Sub 验证 |
| M9 | 全平台集成测试 |
| M10 | CI + lint + typecheck + coverage → **v1.0** |

## 四、测试框架（参照疼痛科）

| 层级 | 目标 |
|------|------|
| 单元测试 | 每个 `modules/` 核心函数 ≥ 3 场景 |
| A2A 分发 | 每个 Agent 的 list_tools + 1 核心 tool |
| 异常场景 | 高危场景触发验证 |
| YAML 校验 | JSON Schema + rules 语法 |
| 注册表 | Agent 类型/端口/依赖一致性 |
| E2E | 每个业务 Agent 至少 1 条临床路径 |
| conftest.py | 共享 mock_llm_provider / sample_patient |

## 五、与老系统的关键差异

| 维度 | v0.2.0 | v1.0 |
|------|--------|------|
| Agent 定义 | Python 子包 + 胶水代码 | YAML + 业务逻辑 |
| A2A 路由 | 硬编码 A2A_AGENTS | 自动从 YAML 生成 |
| 引擎位置 | 业务包内 | 独立 pip 包 |
| LLM 调用 | urllib 直连 | Provider 抽象 + retry + Mock |
| 知识库 | YAML 遍历 | SQLite 同步 |
| 编排 | 顺序 for | asyncio 并行 |
| 测试 | ~5% | ≥ 80% 引擎 + CI |
