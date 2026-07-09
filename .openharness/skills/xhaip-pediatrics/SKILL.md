---
type: guideline
name: xhaip-pediatrics
description: 儿科智能体。生长发育评估 (身高/体重/BMI 百分位) / 儿童用药剂量计算 (按体重/体表面积) / WHO IMCI 常见病诊断辅助 (肺炎/胃肠炎)。3 个 A2A 工具。
trust_level: T1
source:
  - D:\FC\xhaip\packages\haip-hospital\agents\definitions\pediatrics.yaml
  - D:\FC\xhaip\packages\haip-hospital\modules\pediatrics\__init__.py
---

# 儿科智能体

## 工具

| 工具 | 说明 | 示例 |
|------|------|------|
| growth_assess | 生长发育评估 | BMI 百分位计算 |
| dose_calculate | 儿童剂量 | 阿莫西林 50mg/kg × 15kg = 750mg |
| imci_diagnose | IMCI 诊断 | fever+cough+tachypnea → pneumonia |

## 示例

```python
# 剂量计算
call("pediatrics", "dose_calculate", {"drug_name": "amoxicillin", "weight_kg": 15})
# → dose_mg: 750, frequency: "tid", max_daily_mg: 2250

# IMCI 诊断
call("pediatrics", "imci_diagnose", {"symptoms": ["fever","cough","tachypnea"], "age_months": 24})
# → diagnosis: "pneumonia", treatment: "amoxicillin"
```
