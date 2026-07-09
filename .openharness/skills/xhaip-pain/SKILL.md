---
type: guideline
name: xhaip-pain
description: 疼痛专病管理体系。Hub + 5 Sub-agents 树形拓扑: 分诊 → 急性/慢性/癌性/介入/康复。6 个 Agent x 3 工具 = 18 个 A2A 调用入口。完整覆盖从急性术后到终身癌痛管理。
trust_level: T1
source:
  - D:\FC\xhaip\packages\haip-hospital\agents\definitions\pain-hub.yaml
---

# 疼痛专病管理体系

## 树形拓扑

```
pain-hub (分诊)
  ├── acute-pain            # 急性疼痛 (NRS/VAS/PCA)
  ├── chronic-pain          # 慢性疼痛 (生物心理社会/ODI/DN4)
  ├── cancer-pain           # 癌性疼痛 (WHO阶梯/阿片安全)
  ├── interventional-pain   # 介入疼痛 (影像门控/术后安全)
  └── pain-rehab            # 疼痛康复 (运动处方/合并症)
```

## Hub 分诊逻辑

```python
call("pain-hub", "triage", {
    "pain_type": "acute", "vas_score": 8,
    "description": "cauda equina symptoms"
})
# → route_to: "acute-pain", urgency: "critical"
# → red_flags: ["cauda_equina_syndrome"]
```

## WHO 三阶梯癌痛

```python
call("cancer-pain", "assess_cancer", {"vas_score": 8, "current_opioid_mg": 80})
# → who_step: 3, breakthrough_dose_mg: 12.0
```
