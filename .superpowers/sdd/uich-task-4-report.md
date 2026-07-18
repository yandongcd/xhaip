# UI 契约加固 — Task 4 报告

**Date:** 2026-07-17
**Commit:** `8ee4279` (`test: 全站 UI 契约测试 C1-C7 (DOM/JS/API 一致性兜底)`)
**Status:** DONE

## Test Summary

```
tests/test_ui_contracts.py: 45 passed, 13 skipped, 0 failures
```

### C1-C7 breakdown

| Contract | Tests | Passed | Skipped | Purpose |
|----------|-------|--------|---------|---------|
| C1/C7 | 13 | 13 | 0 | JS `getElementById` / `querySelector` → DOM `id=` match |
| C2 | 13 | 13 | 0 | `onclick="foo("` → `function foo(` defined |
| C3 | 13 | 2 | 11 | embedded `PATIENTS` non-empty + has `patient_id` |
| C4 | 4 | 4 | 0 | embedded `AGENT` var == route agent name |
| C5 | 13 | 11 | 2 | `fetch('/static/path')` → registered in FastAPI routes |
| C6 | 2 | 2 | 0 | `WORKFLOWS[].stages[].tool` → agent `tools[].name` |

## Verification — Inject-Fail-Revert

| Step | Action | Result |
|------|--------|--------|
| 1 | Injected `id="hp-stagex"` in `ui_workflow.py:216` (was `hp-badge`) | — |
| 2 | `pytest tests/test_ui_contracts.py -k c1 -q` | **2 FAILED** — caught `hp-badge` missing from DOM on both `/workflow/orthopedic-surgery` and `/workflow/pharmacy` |
| 3 | Reverted edit manually | — |
| 4 | `pytest tests/test_ui_contracts.py -k c1 -q` | **13 passed** — green again |

## Cleanup

Removed `test_workflow_js_ids_exist` from `tests/test_html_pages.py:130-137` (superseded by sitewide C1). Replaced with comment: `# JS id 契约已由 test_ui_contracts.py C1 全站覆盖`.

## Concerns

- **Pre-existing (unrelated):** `TestDemoPage` 6 failures in `tests/test_html_pages.py` — `docs/xhaip-agent-demo.html` uses `let AGENTS = []` (dynamic fetch) instead of `const AGENTS = [...]` (static embed). This is a known pre-existing issue, not introduced by Task 4.

## Files Changed

- `tests/test_ui_contracts.py` — **new** (126 lines)
- `tests/test_html_pages.py` — deleted 8-line method, added 1-line comment

## Controller 补充证据 (C4 注入证明 + lint)
- inject var AGENT='POLLUTED' -> pytest -k c4: 2 failed (workflow 两页) [拦截成功]
- revert -> 全量 45 passed, 13 skipped
- ruff: All checks passed; mypy: 仅 import-not-found (repo-root 运行 tests/ 的既有环境模式, 质量门禁 mypy 范围为 packages/haip-core/haip/)
