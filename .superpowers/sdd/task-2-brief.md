### Task 2: 清理 tests/test_antiemetic.py 死路径

**Files:**
- Modify: `tests/test_antiemetic.py:14-16`

**Interfaces:**
- Consumes: `tests/conftest.py`（已把 `packages/haip-hospital/modules` 注入 sys.path）
- Produces: 无 — 删除后测试行为不变（conftest 兜底已验证：35 passed）

- [ ] **Step 1: 删除死路径**

删除 `tests/test_antiemetic.py` 第 14-16 行：

```python
import sys

sys.path.insert(0, r"D:\FC\xhaip\packages\haip-hospital\modules")
```

即文件从：

```python
import sys

sys.path.insert(0, r"D:\FC\xhaip\packages\haip-hospital\modules")

import pytest
```

改为：

```python
import pytest
```

（`sys` 在文件其余 314 行中无其他使用，已核实。）

- [ ] **Step 2: 验证测试通过**

Run: `python -m pytest tests/test_antiemetic.py -q`
Expected: `35 passed`

- [ ] **Step 3: 提交**

```bash
git add tests/test_antiemetic.py
git commit -m "fix: 移除 test_antiemetic 指向已删除外部目录 D:\FC 的 sys.path"
```

---

