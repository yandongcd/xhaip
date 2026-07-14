# Orthoportal Review Fixes Report

## Fix 1 (I1): Remove `V1_ENDPOINTS` dead code + fix its test

**HTML** (`ui_ortho_portal.html`): Deleted line 103 — `const V1_ENDPOINTS = [...]` (8-element array). The array was unused; runtime code builds paths dynamically via `"/api/v1/orthopedic/"+api`.

**Test** (`test_ortho_portal.py`): Rewrote `test_run_capability_dispatch` (class `TestPortalKpiAndRun`). Instead of asserting each full literal path `/api/v1/orthopedic/<api>` (which relied on the dead constant), it now asserts:
1. `'/api/v1/orthopedic/'` appears in the body (the v1 prefix used by `runCapability`)
2. `'runCapability'` function name appears in the body
3. All 8 CAPS `api` identifiers (`classify`, `assess`, `mdt`, `timing`, `complications`, `plan`, `rehab`, `followup`) appear in the body

This meaningfully verifies capability dispatch wiring without requiring a dead constant.

## Fix 2 (I2): `computeKpi` denominator undercount

**HTML** (`ui_ortho_portal.html`): Replaced the variable `n` (which only incremented when BOTH timing and complications calls succeeded) with `const total = ids.length` used consistently as denominator. This makes `kpi-total`, `kpi-48h` and `kpi-avgfactor` use the same denominator (`total`) so KPIs stay consistent when a call partially fails. Per-patient try/catch is preserved so one failure doesn't abort the loop. Empty-list short-circuit and `total === 0` `"—"` guard remain.

## Fix 3 (M3): `badge()` elective mapping

**HTML** (`ui_ortho_portal.html`):
- Added CSS rule `.badge.elective{background:rgba(10,132,255,.15);color:var(--accent)}` alongside other `.badge.*` rules (after `.badge.low`).
- Changed `badge()` map entry from `elective:"high"` → `elective:"elective"`, so 择期 (lowest urgency) renders with blue accent instead of red high-risk style.

## Fix 4 (M2): trailing newline

**HTML** (`ui_ortho_portal.html`): Ensured file ends with a single trailing newline after `</html>`.

## Test Results

```
$env:HAIP_TEST_MODE="true"; $env:PYTHONPATH="packages/haip-core;packages/haip-hospital;packages/haip-hospital/modules"; python -m pytest tests/integration/test_ortho_portal.py -q

...................                                                      [100%]
19 passed, 1 warning in 1.07s
```

**All 19 tests pass.**

## Ruff

```
$env:PYTHONPATH="packages/haip-core;packages/haip-hospital;packages/haip-hospital/modules"; python -m ruff check tests/integration/test_ortho_portal.py

All checks passed!
```

## Files Changed

- `packages/haip-core/haip/ui_ortho_portal.html` — 4 lines removed (V1_ENDPOINTS), denominator fix, badge CSS + mapping, trailing newline
- `tests/integration/test_ortho_portal.py` — `test_run_capability_dispatch` rewritten

## Commit

`b446295` — `fix(ortho): 门户 review 修复 (V1_ENDPOINTS/KPI 分母/elective 徽章/newline)`
