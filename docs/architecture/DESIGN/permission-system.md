# 三层权限系统设计 [DESIGN]

> 源自 haip-0710 `docs/architecture/permission-system-design.md` (973 行)  
> 状态: [未实现] — xhaip 当前无权限系统，此文档为蓝图

## 设计目标

在三层上控制访问:
| 层 | 问题 | 机制 |
|----|------|------|
| U2A | 用户能看见哪些 Agent？ | HMAC Token + `auth_role_agent` 表 |
| A2A | Agent 能调用哪些 Agent？ | `perm_agent_call_policy` 表 + dispatcher 检查 |
| A2D | Agent 能读哪些数据字段？ | OPA Rego + `perm_data_policy` 表 |

## 数据产品抽象层

解耦 52 Agent × ESB 的核心设计:
```
Agent → DataProduct(adapter_class) → HIS/EMR/LIS/PACS/NIS
```
换医院 ESB 供应商: 改 `adapter_class`，0 Agent 代码变更。

预定义数据产品:
- DP-HIS-PATIENT (SENSITIVE) — 患者基本信息
- DP-LIS-LAB — 检验结果
- DP-PACS-EXAM / DP-PACS-IMAGE — 检查影像
- DP-EMR-NOTE (RESTRICTED) — 病程记录
- DP-EMR-DISCHARGE (RESTRICTED) — 出院小结
- DP-NIS-ASSESS — 护理评估
- DP-NIS-VITAL — 生命体征

## OPA 策略

| 策略 | 规则 |
|------|------|
| self-dept | agent_department == patient_department |
| all-dept | 无限制 (specialist / emergency) |
| consulted | 查 `data.consultations[patient_id]` |
| emergency break-glass | emergency agent 全通 |
| admin metadata-only | 管理员只能看元数据 |

## 实现依赖

- PostgreSQL (0710 用 JSONB 字段过滤)
- SQLite adapter (xhaip 需提供 SQLite 方言替代)
- OPA engine (需集成到 xhaip guard 模块)

## 参考数据

haip-0710 `data/sql/schemas/008_permission_schemas.sql` — 完整 DDL
haip-0710 `data/sql/policies/base.rego` — OPA 基础策略
haip-0710 `data/sql/policies/emergency.rego` — 紧急玻璃破碎策略
