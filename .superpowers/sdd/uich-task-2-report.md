# Task 2 Report: ruff PLR1704 + ui_workflow 渲染函数拆分

**Status: DONE**

**Commit:** `a4e3bce`

## Steps Executed

1. **PLR1704 验证:** Rule confirmed working — detects for-loop variables redefining parameters (e.g. `for name in roles.items()` shadows param `name`). Note: assignments within loop body are not caught by this rule, but the actual regression bug (now fixed) is prevented by the refactored structure.

2. **pyproject.toml 启用 PLR1704:** Both root and `packages/haip-core/pyproject.toml` now have `extend-select = ["PLR1704"]`.

3. **全仓检查:** `python -m ruff check packages/haip-core/ tests/` — 0 violations.

4. **ui_workflow.py 拆分:**
   - Extracted `_build_role_pills(roles) -> tuple[str, str]` (lines 10-23)
   - Extracted `_build_stage_nav(stages) -> str` (lines 26-36)
   - Extracted `_build_stage_panels(stages) -> str` (lines 39-69)
   - `render_workflow_ui` signature unchanged, calls all three builders
   - `first_role` semantics changed from `None` to `""`; `{first_role or "attending"}` behavior preserved

5. **Regression:**
   - `ruff check` — 0 errors
   - `mypy` — 0 errors
   - `pytest tests/test_html_pages.py -q` — **50 passed, 6 failed** (6 failures all in TestDemoPage, pre-existing per baseline)

## Concerns

- The 6 TestDemoPage failures are pre-existing (`const AGENTS = [...]` pattern not matched in demo HTML after a prior `let AGENTS = []` refactor) — not caused by this change.
