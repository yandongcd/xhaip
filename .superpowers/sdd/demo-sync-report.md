# Demo Sync Report — 2026-07-17

## Status: ✅ PASSED

- **Commit**: `b100988`
- **Branch**: master
- **Test summary**: `tests/test_html_pages.py` 8/8 TestDemoPage green; `tests/test_ui_contracts.py` 100 passed / 13 skipped (unchanged)

## Root Cause

Commit `58eb844` (`refactor: dynamic agent loading`) replaced `const AGENTS = [...]` with `let AGENTS = [];` and dynamic API fetch. This broke all 5 tests that parse the static `const AGENTS = [...]` via regex (`_parse_html_agents`) and the `test_js_structure` assertion for `const AGENTS = [` literal.

## What Was Done

1. **Restored `const AGENTS = [...]`** inline array synced from YAML source-of-truth (52 YAML definitions).
2. **Patched `loadAgents()`** to mutate the const array (`AGENTS.length = 0; ... .forEach(x => AGENTS.push(x))`) instead of reassigning.
3. **Created `scripts/sync_demo_agents.py`** — idempotent re-run script that regenerates the AGENTS array from YAML, preserving all display fields (dept, tags, mat, depends_on, tools, desc).
4. **Fixed `depends_on` extraction** — YAML stores dicts `{agent: name, version: ...}`; now extracts just agent names.

## Files Changed

| File | Change |
|------|--------|
| `docs/xhaip-agent-demo.html` | `let AGENTS = []` → `const AGENTS = [{...52 entries...}]` + loadAgents patch |
| `scripts/sync_demo_agents.py` | New: YAML→HTML sync script |

## Concerns

- None. The dynamic loading via `/api/agents` remains functional — `loadAgents()` now mutates the const array instead of reassigning. When API is offline, the page falls back to the static YAML-synced data.
