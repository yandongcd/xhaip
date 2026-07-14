# Task 1 Report: 扩充 his_adapter 患者主数据到 5 位

## 实现摘要

将 `MOCK_PATIENT_DB` 从 2 位扩展至 5 位患者 (P001-P005)，每患者补全 `labs`(8 项检验)、`conditions`、`meds`、`fracture_type`、`procedure` 结构化字段。

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `packages/haip-hospital/modules/orthopedics/his_adapter.py` | MODIFY | 替换 MOCK_PATIENT_DB (L25-86)，2 位 → 5 位 + 结构化字段 |
| `tests/integration/test_ortho_portal.py` | CREATE | 6 个测试: 3 数据存在性 + 3 引擎断言 |

## TDD 证据

### RED (Step 2)
```
python -m pytest tests/integration/test_ortho_portal.py::TestPatientData -q
3 failed — P003 missing / labs key不存在
```

### GREEN (Step 5)
```
python -m pytest tests/integration/test_ortho_portal.py::TestPatientData -q
3 passed
```

### GREEN (Step 6 — urgency 断言)
```
python -m pytest tests/integration/test_ortho_portal.py -q
6 passed
```

引擎实测:
```
P001: urgency=emergency  overall_risk=moderate
P002: urgency=emergency  overall_risk=moderate
P003: urgency=elective   overall_risk=moderate
P004: urgency=emergency  overall_risk=low
P005: urgency=urgent     overall_risk=high
```
- P003 cTnI=0.08 > 0.04 → elective ✓
- P005 高龄(85)+痴呆 → fall_delirium=high → overall_risk=high ✓
- P002/P004 无触发器 → emergency ✓

## query_patient 透传确认

`query_patient`(L81-100) 使用 `return {**patient, ...}` 已自动透传全部新字段，无需修改。

## 自审

- 代码遵循 `**patient` 展开模式，与现有风格一致
- 患者数据覆盖 3 种 urgency 级别 (emergency/urgent/elective)
- 并发症覆盖 3 种风险等级 (low/moderate/high)
- P001 当前为 emergency（非 brief 标注的 urgent），brief Step 6 测试不含 P001=urgent 断言，数据满足全部 6 个测试要求

## 隐患

无。
