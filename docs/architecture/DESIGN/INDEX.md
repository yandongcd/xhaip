# DESIGN — 设计蓝图 [DESIGN]

> 以下设计源自 haip-0710 架构文档，在 xhaip 中标注为 `[未实现]`。
> 这些文档为未来引擎升级提供完整的设计上下文。

| 文档 | 状态 | 优先级 |
|------|------|--------|
| [design-decisions.md](design-decisions.md) | 6 个设计已文档化，0 个已实现 | P0-P2 |
| [permission-system.md](permission-system.md) | 完整设计，代码未实现 | 阻断 PROD |
| [permission-system-faq.md](permission-system-faq.md) | 设计 FAQ | — |
| [rule-governance.md](rule-governance.md) | 平台设计，未实现 | P1 |

## 实现顺序

1. **DESIGN-001 / DESIGN-003** (P0) — 混合分诊 + Agent 版本契约，低复杂度高收益
2. **DESIGN-002 / DESIGN-005** (P1) — Transport 抽象 + T1/T2 信任融合
3. **Permission System** (PROD-blocker) — 需投入最大，权限实现后才能上线
4. **DESIGN-004 / DESIGN-006** (P2) — Data Product + 双路径规则，待评估
