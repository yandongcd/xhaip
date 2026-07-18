# Scripts Path Refactor Report

**Date:** 2026-07-17  
**Branch:** master  
**Commit:** `36b0a46`

## Summary

Replaced hardcoded absolute paths (`D:\FC\xhaip\...`) with `ROOT`-relative paths in 11 utility scripts under `scripts/`.

## Pattern Applied

```python
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
```

All `D:\FC\xhaip\...` and `D:/FC/xhaip/...` paths replaced with `ROOT / "..."` equivalents.
`sys.path.insert()` args converted via `str(ROOT / ...)`.  
`migrate_patients.py`: external legacy `D:\FC\haip-0705-2\data` → `ROOT.parent / "haip-0705-2" / "data"`.

## Affected Files (11)

| File | Absolute Paths Replaced | Notes |
|------|------------------------|-------|
| `scripts/anonymize.py` | 2 × patients.json | |
| `scripts/gen_ortho.py` | 4 × sys.path/load + 1 × html write | |
| `scripts/fix_bp_placeholders.py` | 1 × BP_DIR | `os.listdir`/`os.path.join` based |
| `scripts/expand_patients.py` | 2 × patients.json | |
| `scripts/test_rule_engine.py` | 1 × sys.path + 1 × patients.json | |
| `scripts/test_resp.py` | 1 × sys.path | |
| `scripts/sort_demo_agents.py` | 2 × sys.path + 1 × load + 2 × html | |
| `scripts/gen_patients.py` | 2 × patients.json | |
| `scripts/upgrade_handlers.py` | 1 × MODULES_DIR | `os.listdir` based |
| `scripts/update_rule_abb.py` | 1 × RULES_DIR | `os.walk` based |
| `scripts/migrate_patients.py` | BASE (external) + TARGET_FILE | Already imported Path |

## Verification

- `python -m py_compile scripts/<each>.py` — all 11 passed
- `python -m ruff check scripts/` — 0 new issues (50 pre-existing in other files)

## No Logic Changes

All edits are mechanical path substitutions. No control flow, data, or logic was modified.
