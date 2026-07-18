# Task 1 执行报告: 共享患者加载器 haip/patients.py

## 状态: DONE

## 提交
- **Commit**: `052ddbb` — `refactor: 统一数字病人加载器 haip.patients (B1 共性修复)`
- **分支**: master

## 执行步骤

### Step 1-2: 测试先行 (TDD)
- 写入 `test_patients_loader.py` (8 个测试: dict/list 格式、兼容过滤、回退、limit、缺失文件、损坏 JSON、异常结构)
- 运行确认失败: `ModuleNotFoundError: No module named 'haip.patients'` ✓

### Step 3-4: 实现
- 创建 `packages/haip-core/haip/patients.py`
- `load_patients(agent_name, limit=8, only_compatible=False) -> list[dict]`
- `PATIENTS_FILE: Path` 模块级变量 (可 monkeypatch)
- 运行测试: **8 passed** ✓

### Step 5: ui_workflow.py 重构
- 删除本地 `_load_patients`、`PROJECT_ROOT`、`PATIENTS_FILE`、`from pathlib import Path`
- 替换为 `from haip.patients import load_patients`
- `_load_patients(name)` → `load_patients(name)`

### Step 6: ui_process.py 重构
- `_load_patients` 改为薄封装: 调用 `load_patients(agent_name, limit=30, only_compatible=True)`
- 删除不再使用的 `PROJECT_ROOT`、`PATIENTS_FILE`、`from pathlib import Path`

### Step 7: cases.py 静默失败治理
- `except Exception:` → `except Exception as e: logger.warning(...)`

### Step 8: 回归验证
- **pytest**: 66 passed, 6 failed (全部 6 个为已知 TestDemoPage 预存问题，非本任务引入)
  - `test_patients_loader.py`: 8/8 passed
  - `test_p4.py`: 全部 passed
  - `test_html_pages.py` TestWorkflowPages: 5/5 passed
- **ruff**: All checks passed (0 errors)
- **mypy**: Success: no issues found in 3 source files

## 变更清单
| 文件 | 操作 | 行数变化 |
|------|------|---------|
| `packages/haip-core/haip/patients.py` | 新建 | +47 |
| `packages/haip-core/tests/test_patients_loader.py` | 新建 | +72 |
| `packages/haip-core/haip/ui_workflow.py` | 修改 | -5/+4 |
| `packages/haip-core/haip/ui_process.py` | 修改 | -6/+19 |
| `packages/haip-core/haip/knowledge/cases.py` | 修改 | -1/+4 |

## 接口契约 (供后续 Task 使用)
- `haip.patients.load_patients(agent_name: str, limit: int = 8, only_compatible: bool = False) -> list[dict]` ✓
- `haip.patients.PATIENTS_FILE: Path` (module-level, monkeypatch-able) ✓

## 自审发现
- 无偏离 — 严格按 brief 逐行执行
- 预存 TestDemoPage 6 失败 (已确认不可修复)
