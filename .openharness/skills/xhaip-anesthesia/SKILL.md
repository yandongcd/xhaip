---
type: guideline
name: xhaip-anesthesia
description: 围术期麻醉评估。ASA 分级 (1-6) / 困难气道评估 (Mallampati+甲颌距) / 抗凝管理 (华法林/NOAC/抗血小板桥接) / 麻醉方案推荐 (全麻/腰麻)。116 行, 4 函数。
trust_level: T1
source:
  - packages/haip-hospital/agents/definitions/anesthesia-risk.yaml
  - packages/haip-hospital/modules/anesthesia/__init__.py
---

# 围术期麻醉评估

## ASA 分级

| ASA | 定义 | 手术风险 |
|-----|------|---------|
| 1 | 健康患者 | low |
| 2 | 轻度系统性疾病 | low |
| 3 | 重度系统性疾病, 功能受限 | moderate |
| 4 | 持续威胁生命 | high |
| 5 | 濒死 | — |

## 困难气道评估

- Mallampati 1-4 分级
- 甲颌距 (< 6.0cm = 困难)
- 颈活动度

## 抗凝桥接方案 (ACCP)

| 药物 | 停药时间 | 桥接 |
|------|---------|------|
| 华法林 | 5 天, INR<1.5 | LMWH |
| 氯吡格雷/替格瑞洛 | 5-7 天 | 需桥接 |
| 阿司匹林 | 风险获益评估 | 一般不停 |
| NOAC | 48-72h | 一般不需桥接 |

## 麻醉方案

- 下肢手术: ASA≤2→腰麻, ASA=3→腰麻+镇静, ASA≥4→全麻
- 诱导: propofol + rocuronium
- 高龄减量 20-30%
