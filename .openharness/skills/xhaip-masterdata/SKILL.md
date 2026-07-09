---
type: guideline
name: xhaip-masterdata
description: 患者数据中心 + 指标数据中心。全院患者数据的单一真相源 (查询患者/检验/检查) + 全院运营指标 (质量/效率/科室)。3+3 个 A2A 工具。含 3 个预置样本患者 (P001骨科/P002心外/P003儿科)。
trust_level: T1
source:
  - D:\FC\xhaip\packages\haip-hospital\agents\definitions\medical-record.yaml
  - D:\FC\xhaip\packages\haip-hospital\agents\definitions\metrics.yaml
---

# 患者数据中心 + 指标数据中心

## medical-record

```python
call("medical-record", "get_patient", {"patient_id": "P001"})
# → name: "张三", age: 72, diagnosis: "股骨转子间骨折"
# → meds: ["华法林 2.5mg qd"], allergies: ["青霉素"]

call("medical-record", "get_labs", {"patient_id": "P001"})
# → crp: 45, albumin: 32, inr: 2.1, creatinine: 88
```

## metrics

```python
call("metrics", "get_department_metrics", {"department": "orthopedic_surgery", "month": "2026-07"})
# → avg_stay: 8.5, bed_rate: 85.2, infection_rate: 1.2
```
