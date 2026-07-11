# ADR-005: 围术期止吐药智能体架构迁移

| Field | Value |
|-------|-------|
| **Status** | Proposed |
| **Date** | 2026-07-11 |
| **Deciders** | xhaip architecture team |
| **Supersedes** | N/A |

---

## Context

druganalysis 是一个纯前端 HTML 围术期止吐药智能分析与推荐系统，基于 2025 版中国《术后恶心呕吐诊疗指南》（35 条推荐意见）和 2020 版 SAMBA 第四版共识。当前系统存在以下不足：

1. **纯前端无后端** — 无法 A2A 调用，无法被麻醉科/外科/产科/儿科 Agent 复用
2. **规则硬编码** — 16 条管控规则嵌入 JS，不可追溯、难以审计
3. **未覆盖 2025 指南新增维度** — 麻醉管理优化、非药物措施、生活方式干预等 3 个维度完全缺失
4. **无 TOGAF 治理** — 零架构文档、无合规检查、无成熟度评估
5. **无测试** — 缺乏自动化验证

---

## Decision

**将 druganalysis 重构为 xhaip 药剂科下的围术期止吐药智能体子模块**，遵循以下架构决策：

| 维度 | 决策 |
|------|------|
| 架构模式 | Pattern B — 多文件纯函数，不继承 KnowledgeAgent |
| 部署方式 | 作为 pharmacy Agent 的子工具组，不新建独立 Agent |
| 知识库 | YAML 驱动（6 个知识文件），走 TOGAF rule_engine |
| 指南溯源 | 35 条推荐意见全部标注 GRADE 证据等级 + 2025 指南编号 |
| 能力范围 | 全覆盖 — 6 大能力域 + 8 BP + 5 类新药（NK-1/氨磺必利/戊乙奎醚/抗组胺）|
| 测试策略 | 纯函数 100% 覆盖，pipeline ≥ 80%，Mock LLM |

### 模块结构（10 个文件）

```
modules/pharmacy/antiemetic/
├── __init__.py              # 模块导出
├── scoring_engine.py        # Apfel/POVOC/PDNV 评分
├── drug_recommend.py        # 3 级用药方案推荐
├── drug_controls.py         # 7 类禁忌证管控
├── anesthesia_guide.py      # 麻醉管理建议 ★新增
├── nondrug_guide.py         # 非药物干预 ★新增
├── drug_db.py               # 止吐药数据库 ★扩展
├── knowledge_loader.py      # YAML 知识加载
└── pipeline.py              # 8 个 BP 编排
```

### 知识库结构（6 个 YAML）

```
knowledge/
├── guidelines/anti_emetic_2025.yaml       # 35 条推荐意见
├── rules/anti_emetic_regimens.yaml        # 用药方案矩阵
├── rules/anti_emetic_controls.yaml        # 管控规则（7 类）
├── rules/anesthesia_ponv_rules.yaml       # 麻醉管理规则
├── rules/non_drug_interventions.yaml      # 非药物干预规则
└── drug_db_antiemetic.yaml                # 10+ 止吐药数据库
```

---

## Options Considered

### Option A: 独立 Agent（拒绝）
新建 `antiemetic` Agent，独立端口，独立 YAML 定义。

- **Pros**: 完全独立，不干扰 pharmacy
- **Cons**: 药剂科已有 drug_db / drug_rules / prescription_review，止吐药逻辑与药剂科强耦合；增加 Agent 碎片化；用户需额外维护端口和部署

### Option B: 子模块嵌入（采纳）
作为 pharmacy Agent 的子工具组，追加到现有 pharmacy.yaml。

- **Pros**: 复用药剂科 drug_db / rule_engine / A2A 基础设施；统一端口；知识库共建
- **Cons**: pharmacy 模块文件增多，需注意组织结构清晰

### Option C: 保留纯前端 + API 桥接（拒绝）
druganalysis 保留为独立 HTML，通过 REST API 桥接到 xhaip。

- **Pros**: druganalysis 无需改动
- **Cons**: 双维护成本高；无法走 xhaip 的 TOGAF 治理 / A2A 调度 / guard 层

---

## Consequences

### Positive
- 止吐药逻辑可被麻醉科/外科/产科/儿科 Agent 通过 A2A 调用
- 规则 YAML 化后可通过 TOGAF validator 做合规审计
- 纯函数架构可独立单元测试，无需 LLM 依赖
- 填补 2025 指南 3 个新增维度的临床覆盖

### Negative
- pharmacy 模块从 6 个文件扩展到 ~16 个文件，需保持目录结构清晰
- 管控规则从 16 条（JS 硬编码）迁移到 YAML 后需人工校验一致性
- cockpit.html 驾驶舱需适配新的 JSON API 接口

### Mitigation
- 使用 `antiemetic/` 子目录隔离止吐药逻辑
- 编写 rule_migration_test.py 对比新旧规则输出
- cockpit.html 的 /api 端点由 web_server 新增路由提供

---

## References
- 2025 版中国《术后恶心呕吐诊疗指南》（中华麻醉学杂志, 2025;45(9)）
- SAMBA Fourth Consensus Guidelines for PONV (Anesth Analg, 2020;131(2):411-448)
- 术后恶心呕吐防治专家共识（2014）
- ADR-001: TOGAF 10 as Architecture Governance Foundation
