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

# SDD Progress - UI 契约加固

Plan: docs/superpowers/plans/2026-07-17-ui-contract-hardening.md
Base: aaff010

Task 1: complete (commit 052ddbb, review: spec OK; 3 'extras' adjudicated = session B2/B3 fixes, tests committed 773d517)
Audit fixes: #6 5caf535 / #7-#10 5a0e0d0 / #1#2#4 f4b7977 (guard citation 9415cc5, portal guard 0a00183)
Task 2: complete (commit a4e3bce, review: spec PASS 16/22 verifiable, quality PASS; 6 warn-items resolved by controller via后续全量 ruff/pytest 运行)
B6 fix: interventional_pain handler 漂移 + 309 handler 契约测试 (5dfe5a9)
Task 3: complete (commit 7c4472b, review clean both verdicts)
Task 4: complete (commit 8ee4279, review: spec compliant; Important[C4证明缺失]由controller补证据闭环; Minor: FUNC_DEF_RE不识别箭头函数(与brief一致), mypy import-not-found为既有模式)
Task 5: complete (AGENTS.md 门禁 + ruff CI 范围清零; 9 个失败确认为 d6f2c76 既有: 6 DemoPage + 3 togaf, 已用 worktree 基线取证)
Final review: READY (0 Critical/Important; Minor: case_mgr 未走共享加载器 / launch_all 显式端口 / scripts 15处绝对路径 — 记为后续硬化项)
Minor 遗留收尾: PATIENTS_FILE 单源/launch_all 端口解析 + scripts 11 文件绝对路径清零 (36b0a46)
存量失败清零: DemoPage 同步 (b100988) + togaf 3 断言修正; 全量 1555 passed / 0 failed
