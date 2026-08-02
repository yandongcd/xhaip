---
type: guideline
name: xhaip-cardio
description: 心血管外科 + 心脏评估。EuroSCORE II / 抗凝方案(warfarin/NOAC) / 术后管理 + RCRI评分 / ECG 6模式库 / 围术期MI分型 / 高血压管理。153+94 行, 3+3 函数。
trust_level: T1
source:
  - packages/haip-hospital/agents/definitions/cardio-surgery.yaml
  - packages/haip-hospital/agents/definitions/cardio-risk.yaml
---

# 心血管外科 + 心脏评估

## cardio-risk (心脏评估 specialist)

3 个函数, 153 行:

| 函数 | 能力 |
|------|------|
| `evaluate()` | RCRI 评分 (6 因子) + ECG 模式匹配 (6 种) + 心肌酶分析 |
| `evaluate_mi()` | 围术期 MI 分型 (Type1斑块破裂 / Type2供需失衡) |
| `evaluate_htn()` | 高血压分期 (正常/S1/S2/S3) + 术前控制建议 |

### ECG 模式库 (6 种)

| 模式 | 风险 | 围术期处理 |
|------|------|-----------|
| 窦性心动过速 | moderate | 评估原因 (疼痛/贫血/感染) |
| 窦性心动过缓 | low | 排除病理性原因 |
| 心房颤动 | moderate | CHA2DS2-VASc ≥2 需抗凝 |
| ST段抬高 | **critical** | 延迟手术, 紧急 PCI |
| ST段压低 | **critical** | 心内科会诊, 择期手术 |
| VT/VF | **critical** | 立即停止, 紧急处理 |

## cardio-surgery (心血管外科 business)

3 个函数, 94 行:

| 函数 | 能力 |
|------|------|
| `evaluate()` | 简化 EuroSCORE II (年龄/性别/Cr/COPD/DM/CHF/MI) |
| `plan()` | 抗凝方案: 机械瓣(终身华法林) / 生物瓣(3-6月) / CABG(DAPT 12月) |
| `manage()` | 术后管理: ICU 24-48h / 心包填塞/出血/房颤/心梗并发症监测 |
