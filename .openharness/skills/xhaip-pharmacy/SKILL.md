---
type: guideline
name: xhaip-pharmacy
description: 药剂科智能体。营养风险评估 (NRS2002) / TPN 全肠外营养配比计算 / 处方审核 (17条风险规则) / EN vs PN 途径推荐 / 药品信息查询。6 个 A2A 工具, 6 个临床角色视角切换。
trust_level: T1
source:
  - packages/haip-hospital/agents/definitions/pharmacy.yaml
  - packages/haip-hospital/modules/pharmacy/assessment/__init__.py
---

# 药剂科智能体

## YAML 定义 (80 行)

```yaml
name: pharmacy
type: business
port: 8770
tools:
  - assess_nutrition       # NRS2002 评分 + 再喂养 + 电解质
  - calculate_tpn           # TPN 配比计算
  - review_prescription     # 17 条风险规则审核
  - recommend_nutrition_route  # EN vs PN
  - list_medications        # 药品数据库
```

## 核心业务 — NRS2002 评估

```python
def assess_nutrition_risk(patient_id, weight_kg, height_cm, lab_results, age):
    # NRS2002: 疾病严重度(0-3) + 营养状况(0-3) + 年龄(≥70+1)
    # → risk_level: 低/中/高 → recommendations
```

## 示例调用

```python
call("pharmacy", "assess_nutrition", {
    "patient_id": "P001", "weight_kg": 55, "height_cm": 170,
    "lab_results": {"albumin": 28, "crp": 80}, "age": 78
})
# → risk_level: "高", nrs_score: 5
# → "立即启动营养支持 (肠内优先)"
# → "监测再喂养综合征 (K/Mg/P 每日检测)"
```

## 6 角色视角

```yaml
roles:
  - pharmacist                 # 药师 (通用入口)
  - clinical_pharmacist        # 临床药师 (营养评估+TPN计算)
  - review_pharmacist          # 审方药师 (处方审核)
  - iv_compounding_pharmacist  # 静配药师 (TPN配置)
  - attending                  # 主治医师 (诊疗决策)
  - dietitian                  # 营养师 (营养会诊)
```
