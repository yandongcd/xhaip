---
type: guideline
name: xhaip-orthopedic
description: 创伤骨科智能体。骨折分型 (Garden/Evans/AO) / 术前评估 / 手术方案 (THA/HA/PFNA) / 并发症预测 (DVT/感染) / 手术时机决策。6 个 A2A 工具, 依赖心脏评估 + 麻醉评估 + 病历。
trust_level: T1
source:
  - D:\FC\xhaip\packages\haip-hospital\agents\definitions\orthopedic-surgery.yaml
  - D:\FC\xhaip\packages\haip-hospital\modules\orthopedics\__init__.py
---

# 创伤骨科智能体

## 核心流程

```
骨折分型 → 术前评估 → 手术方案 → 手术时机 → 并发症预测 → 随访
  │           │          │
  ├─ cardio-risk     ← A2A
  ├─ anesthesia-risk ← A2A
  └─ medical-record  ← A2A (患者数据)
```

## 工具调用示例

```python
# 骨折分型
call("orthopedic-surgery", "classify_fracture", {
    "xray_findings": {"location": "femoral_neck", "type": "Garden III"}
})
# → classification: "Garden classification", severity: "high"

# 手术方案: 78 岁股骨颈 → THA
call("orthopedic-surgery", "surgical_plan", {
    "fracture_type": "femoral neck", "age": 78
})
# → procedure: "THA"
```
