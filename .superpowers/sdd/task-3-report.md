# Task 3 Report: 清理 8 个 .openharness/skills/*/SKILL.md

## Status: DONE

## What was implemented

Applied the brief's per-file replacement table verbatim to the `source:` YAML block of all 8 SKILL.md files. YAML indentation (`  - `) preserved exactly; only path text changed; `\` → `/`.

| 文件 | 替换数 | 旧 → 新 |
|------|--------|---------|
| xhaip-core (L8-9) | 2 | `D:\FC\xhaip\packages\haip-core` → `packages/haip-core`; `D:\FC\xhaip\docs\specs\xhaip-refactoring-design.md` → `docs/specs/xhaip-refactoring-design.md` |
| xhaip-pharmacy (L7-8) | 2 | `...\agents\definitions\pharmacy.yaml` → `packages/haip-hospital/agents/definitions/pharmacy.yaml`; `...\modules\pharmacy\assessment\__init__.py` → `packages/haip-hospital/modules/pharmacy/assessment/__init__.py` |
| xhaip-pediatrics (L7-8) | 2 | `...\agents\definitions\pediatrics.yaml` → `packages/haip-hospital/agents/definitions/pediatrics.yaml`; `...\modules\pediatrics\__init__.py` → `packages/haip-hospital/modules/pediatrics/__init__.py` |
| xhaip-pain (L7) | 1 | `...\agents\definitions\pain-hub.yaml` → `packages/haip-hospital/agents/definitions/pain-hub.yaml` |
| xhaip-cardio (L7-8) | 2 | `...\agents\definitions\cardio-surgery.yaml` → `packages/haip-hospital/agents/definitions/cardio-surgery.yaml`; `...\agents\definitions\cardio-risk.yaml` → `packages/haip-hospital/agents/definitions/cardio-risk.yaml` |
| xhaip-orthopedic (L7-8) | 2 | `...\agents\definitions\orthopedic-surgery.yaml` → `packages/haip-hospital/agents/definitions/orthopedic-surgery.yaml`; `...\modules\orthopedics\__init__.py` → `packages/haip-hospital/modules/orthopedics/__init__.py` |
| xhaip-anesthesia (L7-8) | 2 | `...\agents\definitions\anesthesia-risk.yaml` → `packages/haip-hospital/agents/definitions/anesthesia-risk.yaml`; `...\modules\anesthesia\__init__.py` → `packages/haip-hospital/modules/anesthesia/__init__.py` |
| xhaip-masterdata (L7-8) | 2 | `...\agents\definitions\medical-record.yaml` → `packages/haip-hospital/agents/definitions/medical-record.yaml`; `...\agents\definitions\metrics.yaml` → `packages/haip-hospital/agents/definitions/metrics.yaml` |

Total: 15 replacements across 8 files.

## Verification results

Step 2 command (run pre- and post-commit, identical output):

```
PS> Select-String -Path ".openharness\skills\*\SKILL.md" -Pattern "D:\\FC" | Measure-Object | Select-Object Count
Count
-----
    0
```

Post-commit `git status --short -- .openharness/skills/` → empty (clean).

## Files changed

All 8 committed in f3dff6b (8 files changed, 15 insertions(+), 15 deletions(-)):
- .openharness/skills/xhaip-anesthesia/SKILL.md
- .openharness/skills/xhaip-cardio/SKILL.md
- .openharness/skills/xhaip-core/SKILL.md
- .openharness/skills/xhaip-masterdata/SKILL.md
- .openharness/skills/xhaip-orthopedic/SKILL.md
- .openharness/skills/xhaip-pain/SKILL.md
- .openharness/skills/xhaip-pediatrics/SKILL.md
- .openharness/skills/xhaip-pharmacy/SKILL.md

Commit: `f3dff6b docs: 8 个 SKILL.md source 路径改为仓库相对路径, 去除 D:\FC 外部引用`
Staged only `.openharness/skills/` — the pre-existing uncommitted WIP elsewhere in the tree was not touched (verified via `git show --stat HEAD`).

## Self-review findings

- One mid-edit error: I initially wrote `packages/haip-hospital/modules/metrics.yaml` for xhaip-masterdata L8 (wrong directory — brief says `agents/definitions/metrics.yaml`). Caught during post-edit line inspection and corrected before committing; final diff verified against the brief table line-by-line.
- All source lines now start with exactly `  - ` (two-space + dash) and use forward slashes.
- xhaip-core uses the different prefix per brief (`packages/haip-core` + `docs/...`), applied correctly.
- Verified commit contains exactly the 8 intended files — no WIP leakage.
- CRLF warnings from git are pre-existing repo line-ending config behavior; content diff is 1:1 path substitution (4 lines changed per 2-entry file = 2 lines replaced), no accidental reformatting.

## Issues / concerns

- None blocking. The `.openharness/skills/` directory is a sync mirror of source module SKILL.md files (per AGENTS.md, `xhaip sync-skills`); if a future sync re-derives these files from packages/, the source-of-truth files there may still contain `D:\FC` paths — not part of this task's scope, but worth noting for later tasks.
