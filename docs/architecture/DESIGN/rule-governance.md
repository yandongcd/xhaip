# 规则治理平台设计 [DESIGN]

> 源自 haip-0710 `docs/architecture/rule-governance.md` (131 行)  
> 状态: [未实现] — xhaip 规则为 YAML static

## 设计原则

1. **双路径调用**: BaseTool (inline) + A2A Dispatcher (cross-agent)
2. **混合引擎**: DSL 表达式 (90%) + Python 回调 (10%)
3. **五层来源**: L1 (国家法规) → L2 (国际指南) → L3 (专家共识) → L4 (医院制度) → L5 (科室经验)
4. **T1/T2 信任映射**: L1-L3 = T1 (不可变) | L4-L5 = T2 (可覆盖)
5. **五层仲裁**: 优先级链 — 国家法规 > 国际指南 > 专家共识 > 医院制度 > 科室经验

## 当前状态

xhaip 规则库使用 YAML static values + LLM inference 组合。未实现 DSL evaluator 和 arbitration engine。

## 0710 源代码参考

- `src/agents/rules/expr_evaluator.py` — DSL 表达式引擎
- `src/agents/rules/arbitration_engine.py` — 冲突仲裁
- `src/agents/rules/impact_analyzer.py` — 影响分析
