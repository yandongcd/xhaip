# 创伤骨科 TOGAF 10 架构分析

> 基于 TOGAF 元模型自顶向下推导：组织角色 → 价值流 → 业务流程 → 诊疗阶段 × 角色矩阵

---

## 1. 组织角色（TOGAF Organization — 6 角色）

| 角色 | ID | 关注领域 |
|------|-----|---------|
| 科主任 | traumaortho_head | 学科建设、质控指标、MDT 决策、人才梯队、科研产出、设备规划、预算管理、指南制定、疑难会诊、绩效考核 |
| 主治医师 | traumaortho_attending | 诊断确认、手术指征、方案制定、并发症评估、MDT 协调、指南遵循、术前讨论、术后管理、随访计划、带教 |
| 住院医师 | traumaortho_resident | 病史采集、体格检查、医嘱执行、病程记录、检验追踪、术前准备、术后观察、交接班、患者沟通、技能训练 |
| 护士长 | traumaortho_head_nurse | 护理质控、DVT 预防、压疮管理、疼痛评估、体位管理、急救演练、院感防控、耗材管理、排班、出院指导 |
| 责任护士 | traumaortho_staff_nurse | 生命体征、用药执行、管道护理、皮肤护理、翻身拍背、健康教育、出入量记录、跌倒预防、心理护理、交接班 |
| 麻醉医师 | traumaortho_anesthesiologist | 气道评估、ASA 分级、心血管风险、抗凝桥接、容量管理、凝血监测、过敏史、PONV 预防、术中监测、苏醒管理 |

**YAML Agent 选用 3 个角色用于 UI 展示**：主治医师 (attending)、麻醉医师 (anesthesiologist)、护士长 (head_nurse)

---

## 2. 价值流（TOGAF 4A — 5 个）

```
分诊登记 → 诊断与评估 → 多学科决策 → 治疗执行 → 康复随访
```

| # | 价值流 | 触发条件 | 输出 | 参与者 |
|---|--------|---------|------|--------|
| 1 | 分诊登记 | 患者到达 | 分诊级别 (I/II/III/IV) | 主治医师、护士长 |
| 2 | 诊断与评估 | 分诊完成 | 明确诊断 + 骨折分型 | 主治医师、麻醉医师 |
| 3 | 多学科决策 | 诊断确认 | 手术时机 + MDT 方案 | 主治医师、麻醉医师 |
| 4 | 治疗执行 | MDT 完成 | 手术完成 + 并发症管理 | 主治医师、护士长 |
| 5 | 康复随访 | 治疗完成 | 功能恢复 + 长期管理 | 主治医师、护士长 |

**依据**：国家卫健委 2022《老年髋部骨折诊疗与管理指南》§2-§7 → 5 个价值流

---

## 3. 业务流程（TOGAF 4A → Knowledge YAML）

| # | 业务流程 | 价值流 | Owner | 输入 | 输出 |
|---|---------|--------|-------|------|------|
| 1 | 患者登记与分诊 | 分诊登记 | 主治医师 | 患者信息、病史、体格检查 | 分诊级别、患者档案 |
| 2 | 骨折分型 | 诊断与评估 | 主治医师 | X线正位、X线侧位 | Garden/Evans/AO 分型 |
| 3 | 术前完整性检查 | 诊断与评估 | 主治医师 | 检验/影像/心电图/会诊 | 检查清单、缺失项 |
| 4 | 心脏风险评估 | 多学科决策 | 麻醉医师 | 患者信息、检验、心电图 | RCRI 评分、心脏风险等级 |
| 5 | 麻醉风险评估 | 多学科决策 | 麻醉医师 | 气道评估、凝血功能 | ASA 分级、麻醉方案 |
| 6 | MDT 手术时机决策 | 多学科决策 | 主治医师 | 心脏/麻醉报告、骨折分型 | 手术时机 (急诊/限期/择期) |
| 7 | 并发症预测 | 治疗执行 | 主治医师 | 患者档案、合并症 | DVT/感染/压疮/谵妄风险 |
| 8 | 手术方案制定 | 治疗执行 | 主治医师 | 骨折分型、并发症评估 | 手术方式 (THA/PFNA/空心钉) |
| 9 | 围术期护理 | 治疗执行 | 护士长 | 患者信息、手术方式 | 4 阶段护理方案 |
| 10 | 随访管理 | 康复随访 | 主治医师 | 手术记录、出院方案 | 随访计划、Harris 评分 |

**Knowledge 层**：7 份 BP YAML + 22 份规则 YAML + 9 份指南 YAML

---

## 4. 诊疗阶段 × 角色矩阵

| 诊疗阶段 | 主治医师 | 麻醉医师 | 护士长 | 科主任 | 住院医师 | 责任护士 | 工具 | 价值流 |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|------|--------|
| 1. 急诊分诊 | ● | | ● | ○ | ● | ● | checklist | 分诊登记 |
| 2. 骨折分型 | ● | | | ○ | ● | | classify_fracture | 诊断与评估 |
| 3. 术前评估 | ● | ● | | ○ | ● | ● | preop_assessment | 诊断与评估 |
| 4. 手术时机 | ● | ● | | ○ | | | timing_decision | 多学科决策 |
| 5. 并发症预测 | ● | | | ○ | | | complication_risk | 治疗执行 |
| 6. 手术方案 | ● | | | ○ | | | surgical_plan | 治疗执行 |
| 7. 围术期护理 | ● | | ● | ○ | ● | ● | nursing_plan | 治疗执行 |
| 8. 术后康复 | ● | | ● | ○ | ● | ● | rehab_track | 治疗执行 |
| 9. 随访计划 | ● | | ● | ○ | | ● | followup_plan | 康复随访 |
| 10. 质控审计 | ● | | | ● | | | quality_audit | 康复随访 |

> ● = 主要参与（YAML 定义）  
> ○ = TOGAF 角色池中存在但 YAML 未选入 UI

---

## 5. 数据实体（TOGAF 4A — 7 个）

| 数据实体 | 类别 | 字段数 | 被访问者 |
|---------|------|--------|---------|
| 患者信息 | Master | 7 (id/name/age/gender/weight/height/diagnosis) | 4 BP |
| 检验报告 | Transaction | 7 (alb/crp/cr/hb/trop/inr/glu) | 4 BP |
| 影像报告 | Transaction | 4 (xray_ap/lat/CT/MRI) | — |
| 风险评估报告 | Analytics | 4 (RCRI/ASA/complications/timing) | — |
| 手术记录 | Transaction | 5 (type/approach/implant/duration/blood_loss) | — |
| 随访记录 | Transaction | 4 (harris/xray/rehab/complications) | — |
| 术前检查清单 | Reference | 4 (items/completed/missing/status) | — |

---

## 6. 应用组件（TOGAF 4A — 4 个）

| 组件 | 端口 | 依赖 | 服务数 |
|------|------|------|--------|
| 创伤骨科 Agent | 8765 | cardio-risk, anesthesia-risk, medical-record | 15 |
| 心脏风险评估 Agent | — | — | 3 |
| 麻醉风险评估 Agent | — | — | 3 |
| 患者数据中心 | 8766 | — | 3 |

**A2A 通信**：骨科 Agent ← A2A → 心脏风险评估、麻醉评估、患者数据中心

---

## 7. 发现的问题

| 问题 | 现状 | 建议 |
|------|------|------|
| YAML 角色 3/6 | 只选了主治/麻醉/护士长 | 考虑增加科主任（质控审计阶段）、责任护士（护理阶段） |
| 科主任无参与阶段 | 质控审计阶段已定义但矩阵中无 ● | 质控审计应增加科主任为 primary |
| 住院医师无参与阶段 | TOGAF 有 10 项关注领域但未被任何阶段引用 | 急诊分诊/术前评估/围术期护理应加入住院医师 |
| 数据实体访问不完整 | 影像/风险/手术/随访记录无 BP 访问边 | builder.py 需完善 edge 生成逻辑 |
| YAML stages 角色字段 vs TOGAF roles | YAML 用自由文本 "主治医师 / 麻醉医师"，TOGAF 用 role_id | 统一为 role_id 数组 |

---

## 8. 规则体系（Knowledge — 22 份）

```
complication_rules.yaml    fracture_classification_rules.yaml   fracture_evans_rules.yaml
timing_rules.yaml           surgery_type_rules.yaml              nursing_rules.yaml
followup_rules.yaml         rehab_rules.yaml                     osteoporosis_rules.yaml
checklist_rules.yaml        completeness_rules.yaml              risk_alert_rules.yaml
cardio_mi_rules.yaml        ecg_patterns/rules.yaml              rcri/rules.yaml
hip_fracture_timing/rules.yaml  perioperative_mi/rules.yaml       hypertension/rules.yaml
nutrition_rules.yaml        conflict_policy.yaml                 registry.yaml
togaf-governance-rules.yaml
```

---

*生成时间: 2026-07-10 | 基于 TOGAF 10 元模型 + haip.togaf 模块自顶向下分析*
