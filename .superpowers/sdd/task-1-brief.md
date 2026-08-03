### Task 1: 根目录 sitecustomize.py 自举（TDD）

**Files:**
- Create: `sitecustomize.py`（xhaip 根目录）
- Test: `tests/test_self_contained.py`（本任务只写注入断言部分）

**Interfaces:**
- Consumes: 无
- Produces: `sitecustomize` 模块 — 无公开 API；副作用为把 3 个内部路径按序 `sys.path.insert(0, ...)`（去重、目录不存在时跳过）。Task 7 复用同一测试文件追加扫描测试。

- [ ] **Step 1: 写失败测试**

创建 `tests/test_self_contained.py`：

```python
"""xhaip 自包含回归测试：仓库内不得引用 xhaip 文件夹之外的路径/包。"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_BACKSLASH = chr(92)
_FORBIDDEN_PATTERNS = (
    "D:" + _BACKSLASH + "FC",
    "D:" + "/" + "FC",
    "D:" + _BACKSLASH + "dst" + _BACKSLASH + "projects" + _BACKSLASH + "haip",
    "D:" + "/" + "dst" + "/" + "projects" + "/" + "haip",
    "C:" + _BACKSLASH + "Users",
    "C:" + "/" + "Users",
)

_SKIP_DIRS = {
    ".git", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "htmlcov", ".audit", ".code-review-graph", "releases", "node_modules",
    ".superpowers",
}
_SKIP_PREFIXES = (
    os.path.join("docs", "superpowers", ""),
)
_TEXT_SUFFIXES = {
    ".py", ".md", ".yaml", ".yml", ".bat", ".ps1", ".toml", ".json",
    ".txt", ".cfg", ".ini", ".sh", ".example",
}


def _iter_text_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir != ".":
            rel = rel_dir + os.sep
            if any(rel.startswith(p) for p in _SKIP_PREFIXES):
                dirnames[:] = []
                continue
        for name in filenames:
            if Path(name).suffix.lower() in _TEXT_SUFFIXES:
                yield Path(dirpath) / name


def test_sitecustomize_injects_internal_paths():
    importlib.import_module("sitecustomize")
    importlib.reload(sys.modules["sitecustomize"])
    for rel in ("packages/haip-core", "packages/haip-hospital",
                "packages/haip-hospital/modules"):
        assert str(ROOT / rel) in sys.path, f"{rel} 未注入 sys.path"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_self_contained.py::test_sitecustomize_injects_internal_paths -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sitecustomize'`（根目录下尚不存在该文件）

- [ ] **Step 3: 创建 sitecustomize.py**

创建 `sitecustomize.py`（xhaip 根目录，与 pyproject.toml 同级）：

```python
"""xhaip 免安装自举：启动时注入内部包路径，无需 pip install -e。

Python 启动时若仓库根目录在 sys.path 上（从根目录运行 python -m ...），
本文件自动执行，使 packages/ 下的包无需安装即可导入。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

_INTERNAL_DIRS = (
    "packages/haip-core",
    "packages/haip-hospital",
    "packages/haip-hospital/modules",
)

for _rel in _INTERNAL_DIRS:
    _d = ROOT / _rel
    if _d.is_dir():
        _p = str(_d)
        if _p not in sys.path:
            sys.path.insert(0, _p)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_self_contained.py::test_sitecustomize_injects_internal_paths -q`
Expected: PASS

- [ ] **Step 5: 验证零安装启动**

Run: `python -c "import haip; print(haip.__file__)"`
Expected: 打印 `...\packages\haip-core\haip\__init__.py`（来自仓库内部路径，而非 site-packages）

- [ ] **Step 6: 提交**

```bash
git add sitecustomize.py tests/test_self_contained.py
git commit -m "feat: 根目录 sitecustomize 自举, 免 pip install 即可运行 (self-contained)"
```

---

