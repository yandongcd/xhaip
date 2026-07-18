### Task 1: 共享患者加载器 haip/patients.py

**Files:**
- Create: `packages/haip-core/haip/patients.py`
- Create: `packages/haip-core/tests/test_patients_loader.py`
- Modify: `packages/haip-core/haip/ui_workflow.py:1-24` (删除本地 `_load_patients`)
- Modify: `packages/haip-core/haip/ui_process.py:471-485` (`_load_patients` 改为薄封装)
- Modify: `packages/haip-core/haip/knowledge/cases.py:32` (静默 except → logger.warning)

**Interfaces:**
- Produces: `haip.patients.load_patients(agent_name: str, limit: int = 8, only_compatible: bool = False) -> list[dict]`
- Produces: `haip.patients.PATIENTS_FILE: Path` (供测试 monkeypatch)

- [ ] **Step 1: 写失败测试**

```python
# packages/haip-core/tests/test_patients_loader.py
"""共享患者加载器测试 — dict/list 格式、兼容过滤、异常回退."""

from __future__ import annotations

import json

import haip.patients as patients_mod
from haip.patients import load_patients


def _write(tmp_path, payload) -> None:
    f = tmp_path / "patients.json"
    f.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return f


PTS = [
    {"patient_id": "P001", "name": "张三", "compatible_agents": ["orthopedic-surgery"]},
    {"patient_id": "P002", "name": "李四", "compatible_agents": ["pharmacy"]},
    {"patient_id": "P003", "name": "王五", "compatible_agents": ["orthopedic-surgery"]},
]


class TestLoadPatients:
    def test_dict_format(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", _write(tmp_path, {"total": 3, "patients": PTS}))
        result = load_patients("orthopedic-surgery")
        assert [p["patient_id"] for p in result] == ["P001", "P003"]

    def test_list_format(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", _write(tmp_path, PTS))
        result = load_patients("pharmacy")
        assert [p["patient_id"] for p in result] == ["P002"]

    def test_no_match_falls_back_to_all(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", _write(tmp_path, {"patients": PTS}))
        result = load_patients("no-such-agent", limit=2)
        assert len(result) == 2

    def test_only_compatible_no_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", _write(tmp_path, {"patients": PTS}))
        assert load_patients("no-such-agent", only_compatible=True) == []

    def test_limit(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", _write(tmp_path, {"patients": PTS}))
        assert len(load_patients("orthopedic-surgery", limit=1)) == 1

    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", tmp_path / "nope.json")
        assert load_patients("orthopedic-surgery") == []

    def test_corrupt_json_warns(self, tmp_path, monkeypatch, caplog):
        f = tmp_path / "patients.json"
        f.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", f)
        with caplog.at_level("WARNING"):
            assert load_patients("orthopedic-surgery") == []
        assert "patients.json" in caplog.text

    def test_unexpected_structure(self, tmp_path, monkeypatch):
        monkeypatch.setattr(patients_mod, "PATIENTS_FILE", _write(tmp_path, "just a string"))
        assert load_patients("orthopedic-surgery") == []
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest packages/haip-core/tests/test_patients_loader.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'haip.patients'`

- [ ] **Step 3: 实现 haip/patients.py**

```python
# packages/haip-core/haip/patients.py
"""数字病人统一加载 — 全部 UI 渲染器共用的唯一入口.

patients.json 支持两种顶层格式:
  - dict: {"total": N, "patients": [...]}
  - list: [...]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PATIENTS_FILE = PROJECT_ROOT / "packages" / "haip-hospital" / "data" / "patients.json"


def load_patients(agent_name: str, limit: int = 8, only_compatible: bool = False) -> list[dict]:
    """加载与 agent 兼容的数字病人.

    Args:
        agent_name: Agent 技术名, 匹配 patient["compatible_agents"].
        limit: 返回条数上限.
        only_compatible: True 时无兼容患者返回 [] (不回退全量).
    """
    if not PATIENTS_FILE.exists():
        logger.warning("patients.json 不存在: %s", PATIENTS_FILE)
        return []
    try:
        data = json.loads(PATIENTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("patients.json 加载失败: %s", e)
        return []
    all_pts = data.get("patients", []) if isinstance(data, dict) else data
    if not isinstance(all_pts, list):
        logger.warning("patients.json 顶层结构异常: %s", type(all_pts).__name__)
        return []
    matched = [p for p in all_pts if agent_name in p.get("compatible_agents", [])]
    if matched:
        return matched[:limit]
    if only_compatible:
        return []
    return all_pts[:limit]
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest packages/haip-core/tests/test_patients_loader.py -q`
Expected: 8 passed

- [ ] **Step 5: ui_workflow.py 改用共享加载器**

`packages/haip-core/haip/ui_workflow.py` 头部 (1-24 行) 替换为:

```python
"""工作流 UI — process 同款三栏布局 + 角色 stage 筛选 + 工具执行."""

from __future__ import annotations

import json

from haip.patients import load_patients
```

函数内 `patients = _load_patients(name)` 改为 `patients = load_patients(name)`。
删除本地 `_load_patients`、`PROJECT_ROOT`、`PATIENTS_FILE`、`from pathlib import Path`。

- [ ] **Step 6: ui_process.py 改用共享加载器**

`packages/haip-core/haip/ui_process.py:471-485` 的 `_load_patients` 替换为:

```python
def _load_patients(agent_name: str) -> list[dict]:
    """从 patients.json 加载与给定 agent 兼容的患者数据。"""
    from haip.patients import load_patients

    matched = load_patients(agent_name, limit=30, only_compatible=True)
    if matched:
        return _normalize_patients(matched)
    return _fallback_patients()
```

同时删除文件头部不再使用的 `PATIENTS_FILE` 常量 (若 `json`/`Path` 仍被他处使用则保留 import)。

- [ ] **Step 7: cases.py 静默失败治理**

`packages/haip-core/haip/knowledge/cases.py` 顶部加:

```python
import logging

logger = logging.getLogger(__name__)
```

`load()` 中:

```python
            except Exception as e:
                logger.warning("病例文件加载失败 %s: %s", f, e)
```

- [ ] **Step 8: 回归验证**

Run: `python -m pytest packages/haip-core/tests/test_patients_loader.py tests/test_html_pages.py packages/haip-core/tests/test_p4.py -q`
Expected: 全部 passed (含 TestWorkflowPages 5 项)

Run: `python -m ruff check packages/haip-core/haip/patients.py packages/haip-core/haip/ui_workflow.py packages/haip-core/haip/ui_process.py packages/haip-core/haip/knowledge/cases.py; python -m mypy packages/haip-core/haip/patients.py packages/haip-core/haip/ui_workflow.py packages/haip-core/haip/ui_process.py`
Expected: 0 errors

- [ ] **Step 9: Commit**

```bash
git add packages/haip-core/haip/patients.py packages/haip-core/tests/test_patients_loader.py packages/haip-core/haip/ui_workflow.py packages/haip-core/haip/ui_process.py packages/haip-core/haip/knowledge/cases.py
git commit -m "refactor: 统一数字病人加载器 haip.patients (B1 共性修复)"
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

