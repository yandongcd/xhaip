# SDD Progress — 创伤骨科诊疗门户

Plan: docs/superpowers/plans/2026-07-13-ortho-portal.md
Branch: master (file-level commits; pre-existing WIP in tree)

- Task 1: 扩充 his_adapter 患者到 5 位 — complete (commit cf1c86e, review clean; reviewer's Important finding on missing `)` was a false positive from diff encoding — verified P002/P004 correct)
  - Minor deferred: unused `client` in test (needed by Tasks 2-5); query_imaging docstring edit is pre-existing WIP
- Task 2: 新增 /ortho-portal 路由 + HTML 骨架 — complete (commit e5907d8, review clean; note: tests use HAIP_TEST_MODE for auth bypass)
- Task 3: 门户 HTML 布局 + 设计令牌 — complete (commit a180d58, review clean, 10/10 tests)
  - Minor deferred: no trailing newline in html; `.p-card.active` bg hardcoded rgba(10,132,255,.12) (light-mode tint mismatch) — consider color-mix in Task 5/final
- Task 4: 门户 JS 患者队列/能力卡/阶段渲染 — complete (commit 5b5ff8d, review clean, 13/13 tests; emoji/wording "drift" findings were diff-encoding false positives)
  - Minor deferred: no trailing newline in html (recurring)
- Task 5: 门户 KPI 聚合 + 能力卡执行 — complete (commit b3d617e, review clean, 19/19 tests)
  - Minor deferred: `V1_ENDPOINTS` const in production JS is a test-only artifact (paths built via concat elsewhere) — consider refining test to assert concat pattern instead
- Task 6: 回归 + Lint + 手动验收 — complete (automated parts)
  - ortho-portal 19/19 + test_orthopedic.py pass; ruff clean; E2E TestClient(HAIP_TEST_MODE=true) OK
  - PRE-EXISTING out of scope: 6 TestDemoPage failures (demo html vs YAML roster) — not touched by this feature
  - auth bypass requires HAIP_TEST_MODE="true"

## Final whole-branch review (30e140e..b3d617e) — Ready to merge WITH FIXES
Fix batch dispatched (I1,I2,M2,M3):
- I1: V1_ENDPOINTS dead code → wire into runtime or remove + fix test
- I2: computeKpi undercounts denominator on partial failure → count n independently
- M2: add trailing newline
- M3: badge() maps elective→"high" red (should be neutral)
Noted, NOT fixing (match existing codebase patterns): I3 innerHTML (36+ uses repo-wide), I4 module-level HAIP_TEST_MODE (same as test_orthopedic.py)
Deferred nice-to-have: M1 color-mix, M4 Promise.all parallelize, M5 error escaping
