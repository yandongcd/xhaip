# 创伤骨科 Agent 业务流来源分析

## 5 层证据链架构

haip-0705-2 的骨科业务流不是凭空设计的，而是遵循一个严格的 **5 层 TOGAF 对齐架构**，从国家标准逐层派生到可执行代码：

```
Layer 0: 国家标准 & 临床指南 (14 PDF)
   ↓ 人工提取关键章节 → stage_id + rule_id 映射
Layer 1: 指南 ABB YAML (10 个)
   ↓ 规则化 → condition_expr + conclusion + evidence
Layer 2: 可执行规则 YAML (6 个规则集, ~200 条规则)
   ↓ 代码加载 → evaluate()
Layer 3: 业务流程 YAML (9 个, ~730 行)
   ↓ import 模块调用
Layer 4: Python 业务模块 (23 个核心模块)
```

## 证据溯源

国家卫健委 2022 版《老年髋部骨折诊疗与管理指南》是最核心的单一来源，贡献了 **65 条可执行规则**：

| 指南章节 | 对应规则集 | 对应模块 |
|---------|-----------|---------|
| §2 急诊评估 | triage rules | core/checklist.py |
| §3 术前准备 | completeness_rules.yaml (14项) | core/completeness.py |
| §4 手术时机 | timing_rules.yaml (六因素) | core/timing_engine.py |
| §5 手术方式 | surgery_type_rules.yaml (10种) | core/surgery_planner.py |
| §6 围术期 | complication + nursing | core/complication_predictor.py + core/nursing_care.py |
| §7 康复随访 | followup_rules.yaml | core/followup.py |

其余 9 个国际/国内指南各贡献 5-25 条规则作为补充：

| 指南 | 贡献规则数 | 补充方向 |
|------|-----------|---------|
| NICE NG37 (UK 2023) | 25 | 手术时机、护理、随访 |
| AAOS 2022 (US) | 20 | 手术方式、VTE预防、康复 |
| CSCO 股骨颈 2018 | 10 | Garden分型、手术方式 |
| CSCO 转子间 2020 | 12 | Evans分型、PFNA |
| EFORT 2021 (EU) | 8 | 心脏/抗凝/贫血术前优化 |
| APTA 2021 (US) | 8 | 4阶段康复 |
| DVT共识 2024 | 8 | Caprini评分、护理 |
| 衰弱护理共识 2023 | 21 | 4阶段护理25项 |
| 南方医院 T2 | 5差异 | T1→T2权重调整 |

## 设计方法论

1. **问题驱动**: 基于真实数据 (中国 48h 手术率仅 6.9%) 定义范围
2. **范围收窄**: 仅覆盖老年髋部骨折围术期 (股骨颈/转子间/转子下)
3. **双轨验证**: T1 (国标) + T2 (院级经验) 层次决策
4. **规则外化**: 临床规则从 Python 硬编码迁移到 YAML (timing v2.0→v3.0)
