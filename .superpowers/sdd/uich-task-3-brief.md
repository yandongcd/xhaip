### Task 3: tests/conftest.py + 恒真断言清理

**Files:**
- Create: `tests/conftest.py`
- Modify: `tests/test_html_pages.py:14-20` (env 设置移入 conftest)
- Modify: `packages/haip-core/tests/test_p4.py:65-73`

**Interfaces:**
- Produces: conftest 自动生效的 `HAIP_TEST_MODE=true` + sys.path 注入 (tests/ 目录下所有测试文件可直接 `from haip.web_server import app`)

- [ ] **Step 1: 写 conftest.py**

```python
# tests/conftest.py
"""tests/ 统一测试环境 — env + sys.path, 消除测试文件间隐式依赖."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for p in (ROOT / "packages" / "haip-core", ROOT / "packages" / "haip-hospital",
          ROOT / "packages" / "haip-hospital" / "modules"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

os.environ.setdefault("HAIP_TEST_MODE", "true")
```

- [ ] **Step 2: test_html_pages.py 移除本地 env 设置**

删除 `os.environ["HAIP_TEST_MODE"] = "true"` 行与 `import os` (若无他用)。sys.path 两行保留 (单文件直跑兼容)。

- [ ] **Step 3: 修复 test_p4.py 恒真断言**

```python
    def test_load_patients(self):
        from haip.knowledge.cases import CaseManager
        data_dir = project_root / "packages" / "haip-hospital" / "data"
        assert data_dir.exists(), "患者数据目录缺失"
        cm = CaseManager()
        cm.load(data_dir)
        assert len(cm.cases) > 0, "患者数据加载为空 — 检查 patients.json 格式"
        s = cm.stats()
        assert "total" in s
```

- [ ] **Step 4: 全仓扫描其他恒真断言**

Run: `python -m pytest --collect-only -q tests/ packages/haip-core/tests/ | Out-Null; Select-String -Path tests\*.py,packages\haip-core\tests\*.py -Pattern "assert.*(>= 0|len\(.*\) >= 0)"`
每个命中逐一判断: 有数据前置条件的改 `> 0`, 纯防御性的保留并注明原因。

- [ ] **Step 5: 验证**

Run: `python -m pytest tests/test_html_pages.py packages/haip-core/tests/test_p4.py -q`
Expected: 全部 passed (单文件独立跑, 不依赖其他测试)

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_html_pages.py packages/haip-core/tests/test_p4.py
git commit -m "test: conftest 统一 HAIP_TEST_MODE + 清理恒真断言"
```

---



---

## Global Constraints

- ruff line-length=100, `ignore=["E402"]` 保持不变, 新增 `extend-select=["PLR1704"]`
- mypy strict=false, 修改文件必须 0 错误
- 不引入新第三方依赖
- 不修改 ui_render.py / ui_ortho*.html / ui_pharmacy*.html 的实现 (契约测试兜底)
- 所有命令在 `D:\FC\xhaip` 执行

---

