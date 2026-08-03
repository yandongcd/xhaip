# Task 1 Report: 根目录 sitecustomize.py 自举 (TDD)

## What I implemented

- **`sitecustomize.py`** (repo root, sibling of `pyproject.toml`): Python startup hook that
  inserts 3 internal package paths into `sys.path` in order, dedup-checking each and
  skipping non-existent dirs:
  `packages/haip-core`, `packages/haip-hospital`, `packages/haip-hospital/modules`.
  Code is verbatim from the task brief (module docstring included, no extra comments).
- **`tests/test_self_contained.py`**: new regression test file per the brief — includes the
  scan infrastructure (`_FORBIDDEN_PATTERNS`, `_SKIP_DIRS`, `_SKIP_PREFIXES`,
  `_TEXT_SUFFIXES`, `_iter_text_files`) that Task 7 will reuse, plus the single
  injection-assertion test for this task:
  `test_sitecustomize_injects_internal_paths` (import + reload `sitecustomize`, then assert
  all 3 paths present in `sys.path`).

## TDD Evidence

### RED

Command:
```
python -m pytest tests/test_self_contained.py::test_sitecustomize_injects_internal_paths -q
```
Output:
```
F  [100%]
E   ModuleNotFoundError: No module named 'sitecustomize'
<frozen importlib._bootstrap>:1335: ModuleNotFoundError
1 failed, 2 warnings in 0.14s
```
Why expected: `sitecustomize.py` did not exist in the repo root (verified with
`Test-Path sitecustomize.py` → False), so `importlib.import_module("sitecustomize")`
cannot resolve. The failure is at the exact intended line, confirming the test
exercises the real mechanism.

(Note: the 2 warnings were a pre-existing `.pytest_cache` WinError 183 race in this
environment, unrelated to the task; failure cause was genuinely the ModuleNotFoundError.)

### GREEN

Command:
```
python -m pytest tests/test_self_contained.py::test_sitecustomize_injects_internal_paths -q -p no:cacheprovider
```
Output:
```
.  [100%]
1 passed in 0.06s
```

### Zero-install bootstrap verification

Command:
```
python -c "import haip; print(haip.__file__)"
```
Output:
```
D:\dst\projects\xhaip\packages\haip-core\haip\__init__.py
```
Confirmed `haip` resolves from the repo-internal path, not site-packages — i.e. the
`pip install -e packages/haip-core` requirement is eliminated at runtime.

### Quality gate

```
ruff check sitecustomize.py tests/test_self_contained.py
→ All checks passed!
```

## Files changed

| File | Action |
|------|--------|
| `sitecustomize.py` | added (repo root) |
| `tests/test_self_contained.py` | added |

Commit: `6e99048` — "feat: 根目录 sitecustomize 自举, 免 pip install 即可运行 (self-contained)"
(exact message from brief). Only these 2 files staged (`git add sitecustomize.py
tests/test_self_contained.py`); the many pre-existing WIP changes were not touched.

## Self-review

- **Completeness:** all 6 brief steps executed: failing test → RED confirmed → implement →
  GREEN confirmed → zero-install `import haip` verified → committed with exact message.
- **Quality:** code is verbatim from the brief; no comments beyond the module docstring;
  ruff clean (line length 100 honored — longest lines are the multi-line tuple literals).
- **Discipline:** only the two task files staged/committed, no `-A`/`.`; working tree's
  pre-existing WIP changes left untouched.
- **Testing:** one focused test asserting all 3 internal dirs are injected after a reload,
  which guards against both missing paths and stale-order regressions.

## Issues / concerns

- `sitecustomize.py` only activates when the repo root is on `sys.path` (e.g. running
  `python -m ...` or `python -c` from the root). This is inherent to the mechanism and
  documented in the module docstring; Task 7's broader scan test will cover repo-wide
  compliance, and the design doc's chosen approach (方案 A) already accounts for this.
- Pre-existing `.pytest_cache` WinError 183 warning in this environment is unrelated to
  this task (bypassed with `-p no:cacheprovider` for the GREEN run).
- The test file currently contains the shared scan helpers (`_iter_text_files` etc.) that
  only get exercised in Task 7 — deliberate per the brief's exact code block, so Task 7
  only appends scan tests.
