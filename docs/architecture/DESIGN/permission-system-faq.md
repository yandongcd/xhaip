# 权限系统 FAQ [DESIGN]

> 源自 haip-0710 `docs/architecture/permission-system-faq.md` (186 行)

## Q: 为什么不用 FHIR？
A: FHIR 是数据交换标准，不是权限模型。权限系统关注"谁能看什么"，FHIR 关注"数据长什么样"。两者正交。

## Q: 为什么不用 JWT？
A: JWT 解决的是认证 (authentication) 身份传递问题。权限系统解决的是授权 (authorization) 问题。两者配合使用，不是替代关系。

## Q: 权限检查对性能的影响？
A: OPA policy evaluation 在微秒级 (预编译 Rego)。A2A 检查在 dispatcher 层缓存策略表。U2A 检查仅在用户登录时执行一次。

## Q: 紧急场景 (break-glass) 如何设计？
A: emergency agent 被 OPA 策略赋予 `all` dept_scope。所有紧急访问记录到 `audit.audit_access_log`，事后审计。

## Q: 会诊场景如何支持？
A: `perm.rel_consultation` 表记录会诊关系。OPA 策略查询 `data.consultations[patient_id]` 动态授权。
