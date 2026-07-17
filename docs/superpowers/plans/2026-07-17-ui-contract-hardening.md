# UI 契约加固实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除 workflow 三连 bug 的共性根因 — 统一患者加载器、全站 UI 契约测试、PLR1704 lint、测试基础设施治理。

**Architecture:** 新建 `haip/patients.py` 作为患者数据唯一加载入口,ui_workflow/ui_process 薄封装调用;新建 `tests/test_ui_contracts.py` 参数化校验所有 HTML 路由的 7 项 DOM/JS/API 契约;`tests/conftest.py` 统一测试环境;ruff 启用 PLR1704 拦截参数遮蔽。

**Tech Stack:** Python 3.10+ / FastAPI TestClient / pytest / ruff 0.15 / mypy

**Spec:** `docs/superpowers/specs/2026-07-17-ui-contract-hardening-design.md`

## Global Constraints

- ruff line-length=100, `ignore=["E402"]` 保持不变, 新增 `extend-select=["PLR1704"]`
- mypy strict=false, 修改文件必须 0 错误
- 不引入新第三方依赖
- 不修改 ui_render.py / ui_ortho*.html / ui_pharmacy*.html 的实现 (契约测试兜底)
- 所有命令在 `D:\FC\xhaip` 执行

---

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

### Task 2: ruff PLR1704 + ui_workflow 渲染函数拆分

**Files:**
- Modify: `pyproject.toml:9-10`
- Modify: `packages/haip-core/pyproject.toml:29-30`
- Modify: `packages/haip-core/haip/ui_workflow.py` (render_workflow_ui 拆分)

**Interfaces:**
- Produces: `_build_role_pills(roles: dict) -> tuple[str, str]` (返回 pills_html, first_role)
- Produces: `_build_stage_nav(stages: list[dict]) -> str`
- Produces: `_build_stage_panels(stages: list[dict]) -> str`
- 均为 ui_workflow.py 模块私有, `render_workflow_ui` 签名不变

- [ ] **Step 1: 验证 PLR1704 能拦截 B3 类缺陷**

```bash
@'
def render(name: str, roles: dict) -> str:
    out = ""
    for rid, cfg in roles.items():
        name = cfg.get("name", rid)
        out += name
    return f"var AGENT='{name}'" + out
'@ | Set-Content -Encoding utf8 C:\Users\12362\AppData\Local\Temp\opencode\shadow_check.py
python -m ruff check --select PLR1704 C:\Users\12362\AppData\Local\Temp\opencode\shadow_check.py
```

Expected: 报 `PLR1704 Redefining argument with the local name 'name'` (证明规则有效, 之后删除临时文件)

- [ ] **Step 2: 两处 pyproject.toml 启用 PLR1704**

根 `pyproject.toml`:

```toml
[tool.ruff.lint]
extend-select = ["PLR1704"]
ignore = ["E402"]
```

`packages/haip-core/pyproject.toml` 的 `[tool.ruff.lint]` 同样加 `extend-select = ["PLR1704"]`。

- [ ] **Step 3: 全仓跑 PLR1704 确认无存量违例**

Run: `python -m ruff check packages/haip-core/ tests/`
Expected: 0 errors (若有存量违例, 逐个用非遮蔽名修复)

- [ ] **Step 4: 拆分 render_workflow_ui**

`packages/haip-core/haip/ui_workflow.py` 中三段内联循环 (角色 Pill / 右侧阶段导航 / 阶段面板) 提取为模块级函数, 置于 `render_workflow_ui` 之前:

```python
def _build_role_pills(roles: dict) -> tuple[str, str]:
    """角色 Pill HTML + 首个角色 id."""
    pills = ""
    first_role = ""
    for rid, rcfg in roles.items():
        if not first_role:
            first_role = rid
        icon = rcfg.get("icon", "")
        label = rcfg.get("name", rid)
        pills += (
            f'<button class="role-pill" data-role="{rid}" '
            f'onclick="switchRole(\'{rid}\')">{icon} {label}</button>\n'
        )
    return pills, first_role


def _build_stage_nav(stages: list[dict]) -> str:
    """右侧阶段导航 HTML."""
    items = ""
    for s in stages:
        items += (
            f'<div class="rb-item" data-stage="{s["order"]}" onclick="clickStage({s["order"]})">'
            f'<span class="rb-dot current"></span>'
            f'<div class="rb-info"><div class="rb-name">{s["order"]}. {s["label"]}</div></div>'
            f'<span class="rb-status active-s">当前</span></div>\n'
        )
    return items


def _build_stage_panels(stages: list[dict]) -> str:
    """阶段面板 HTML (带执行按钮)."""
    panels = ""
    for i, s in enumerate(stages):
        act = " active" if i == 0 else ""
        tool_name = s["tool"]
        panels += (
            f'<div class="stage-content{act}" id="stage-{s["order"]}">'
            f'<div class="stage-header"><span class="stage-badge">{s["order"]}</span>'
            f'<div><h3>{s["label"]}</h3><p>{s["description"]}</p>'
            f'<span class="guide-ref">{s.get("guideline_ref", "")}</span></div></div>'
            f'<div class="form-group"><label>参数</label>'
            f'<textarea id="params-{s["id"]}">'
            f'{{"patient_id":"P001","age":78,"weight_kg":55,"height_cm":170}}</textarea></div>'
            f'<div class="btn-row">'
            f'<button class="btn-exec" onclick="callStage(\'{s["id"]}\',\'{tool_name}\')">'
            f'▶ 执行 {s["label"]}</button>'
            f'<button class="btn-guard" onclick="showGuard(\'{s["id"]}\')">🛡 安全校验</button>'
        )
        if i < len(stages) - 1:
            panels += (
                f'<button class="btn-next" '
                f'onclick="autoNext(\'{s["id"]}\',\'{stages[i + 1]["id"]}\')">→ 下一步</button>'
            )
        panels += (
            f'</div>'
            f'<div class="result-box" id="result-{s["id"]}">'
            f'<span class="result-placeholder">点击「执行」开始...</span></div>'
            f'</div>\n'
        )
    return panels
```

`render_workflow_ui` 中对应三段替换为:

```python
    role_pills, first_role = _build_role_pills(roles)
    sb_items = _build_stage_nav(workflow_stages)
    panels = _build_stage_panels(workflow_stages)
```

注意: 原 `first_role = None` 语义改为空字符串, 模板中 `{first_role or "attending"}` 行为不变。

- [ ] **Step 5: 回归验证**

Run: `python -m pytest tests/test_html_pages.py -q; python -m ruff check packages/haip-core/haip/ui_workflow.py; python -m mypy packages/haip-core/haip/ui_workflow.py`
Expected: TestWorkflowPages 5 项含 AGENT/patients 断言全过, lint/type 0 errors

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml packages/haip-core/pyproject.toml packages/haip-core/haip/ui_workflow.py
git commit -m "refactor: ui_workflow 渲染拆分 + ruff PLR1704 拦截参数遮蔽 (B3 共性修复)"
```

---

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

### Task 4: 全站 UI 契约测试 tests/test_ui_contracts.py

**Files:**
- Create: `tests/test_ui_contracts.py`

**Interfaces:**
- Consumes: conftest.py 的 env/sys.path (Task 3); `haip.workflow.WORKFLOWS`; `haip.agent.get_agent`
- Produces: 7 项契约测试 (C1-C7), 后续新增 UI 页面自动纳入

- [ ] **Step 1: 写契约测试**

```python
# tests/test_ui_contracts.py
"""全站 UI 契约测试 — DOM/JS/API 一致性 (源自 2026-07-17 workflow 三连 bug 复盘).

C1: getElementById 静态 id 必须存在于 DOM
C2: onclick 引用函数必须已定义
C3: 嵌入 PATIENTS 的页面数据非空且含 patient_id
C4: 嵌入 AGENT 的页面其值 == 路由 agent 名
C5: fetch 静态路径必须在 FastAPI 路由表注册
C6: workflow STAGES[].tool 必须存在于 agent tools
C7: querySelector('#x') 静态 id 同 C1
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from haip.agent import get_agent, load_from_dir

ROOT = Path(__file__).resolve().parent.parent
load_from_dir(str(ROOT / "packages" / "haip-hospital" / "agents" / "definitions"))

from haip.web_server import app  # noqa: E402
from haip.workflow import WORKFLOWS  # noqa: E402

client = TestClient(app)

GETELEM_RE = re.compile(r"getElementById\('([\w-]+)'\)")
QS_ID_RE = re.compile(r"querySelector\('#([\w-]+)'\)")
DOM_ID_RE = re.compile(r'id="([\w-]+)"')
ONCLICK_RE = re.compile(r'onclick="(\w+)\s*\(')
FUNC_DEF_RE = re.compile(r'(?:function\s+(\w+)\s*\(|(?:var|let|const)\s+(\w+)\s*=\s*(?:async\s+)?function)')
PATIENTS_RE = re.compile(r'var PATIENTS\s*=\s*(\[.*?\]);', re.DOTALL)
AGENT_RE = re.compile(r"var AGENT\s*=\s*'([^']*)'")
FETCH_RE = re.compile(r"""fetch\(\s*['"](/[^'"$]*)['"]\s*[,)]""")


def _html_pages() -> list[str]:
    pages = ["/", "/ortho", "/ortho-portal", "/pharmacy", "/stream-demo", "/dashboard"]
    pages += [f"/workflow/{n}" for n in WORKFLOWS]
    pages += ["/process/orthopedic-surgery", "/process/respiratory", "/process/cardiology"]
    pages += ["/agent/orthopedic-surgery", "/agent/pharmacy"]
    return pages


PAGES = _html_pages()


def _get(path: str) -> str:
    resp = client.get(path)
    assert resp.status_code == 200, f"{path}: {resp.status_code}"
    return resp.text


@pytest.mark.parametrize("path", PAGES)
def test_c1_c7_js_dom_ids(path):
    html = _get(path)
    js_ids = set(GETELEM_RE.findall(html)) | set(QS_ID_RE.findall(html))
    dom_ids = set(DOM_ID_RE.findall(html))
    missing = js_ids - dom_ids
    assert not missing, f"{path}: JS 引用了不存在的 id: {sorted(missing)}"


@pytest.mark.parametrize("path", PAGES)
def test_c2_onclick_functions_defined(path):
    html = _get(path)
    called = set(ONCLICK_RE.findall(html))
    defined = {a or b for a, b in FUNC_DEF_RE.findall(html)}
    missing = called - defined
    assert not missing, f"{path}: onclick 引用了未定义函数: {sorted(missing)}"


@pytest.mark.parametrize("path", PAGES)
def test_c3_patients_not_empty(path):
    html = _get(path)
    m = PATIENTS_RE.search(html)
    if not m:
        pytest.skip(f"{path} 无嵌入 PATIENTS")
    patients = json.loads(m.group(1))
    assert patients, f"{path}: PATIENTS 为空 — 检查 haip.patients 加载链路"
    assert all("patient_id" in p for p in patients), f"{path}: 患者记录缺 patient_id"


@pytest.mark.parametrize("path", [p for p in PAGES if p.startswith(("/workflow/", "/agent/"))])
def test_c4_agent_var_matches_route(path):
    html = _get(path)
    m = AGENT_RE.search(html)
    assert m, f"{path}: 无 AGENT 变量"
    expected = path.rsplit("/", 1)[-1]
    assert m.group(1) == expected, f"{path}: AGENT 被污染为 {m.group(1)!r}"


@pytest.mark.parametrize("path", PAGES)
def test_c5_fetch_paths_registered(path):
    html = _get(path)
    static_fetches = {p for p in FETCH_RE.findall(html) if "'" not in p and "+" not in p}
    if not static_fetches:
        pytest.skip(f"{path} 无静态 fetch")
    unmatched = []
    for fp in static_fetches:
        fp_clean = fp.split("?")[0]
        ok = any(
            getattr(r, "path", None) == fp_clean
            or (hasattr(r, "path_regex") and r.path_regex.match(fp_clean))
            for r in app.routes
        )
        if not ok:
            unmatched.append(fp)
    assert not unmatched, f"{path}: fetch 了未注册路由: {unmatched}"


@pytest.mark.parametrize("wf_name", sorted(WORKFLOWS))
def test_c6_workflow_tools_exist(wf_name):
    wf = WORKFLOWS[wf_name]
    plugin = get_agent(wf["agent"])
    assert plugin is not None, f"workflow 引用未注册 agent: {wf['agent']}"
    tool_names = {t.name for t in plugin.tools}
    missing = [s["tool"] for s in wf["stages"] if s["tool"] not in tool_names]
    assert not missing, f"{wf_name}: stages 引用不存在的 tool: {missing}"
```

- [ ] **Step 2: 运行**

Run: `python -m pytest tests/test_ui_contracts.py -q`
Expected: 全部 passed 或 skip (当前全站已修复; 若有失败即为存量缺陷, 逐一修复后再过)

- [ ] **Step 3: 证明契约测试有效 (注入-变红-还原)**

1. 临时把 `ui_workflow.py` 中 `id="hp-badge"` 改回 `id="hp-stage"` → `python -m pytest tests/test_ui_contracts.py -k c1 -q` Expected: FAIL (拦截 B2)
2. 还原后, 临时把 `_build_role_pills` 返回的 pills 变量在 `render_workflow_ui` 中赋给 `name` 参数模拟遮蔽 → `-k c4` Expected: FAIL (拦截 B3)
3. `git checkout -- packages/haip-core/haip/ui_workflow.py` 禁用 — 手工还原两处 (安全规约禁止 checkout --)
4. 还原后全量: `python -m pytest tests/test_ui_contracts.py -q` Expected: 全 passed

- [ ] **Step 4: 收敛 test_html_pages.py 中重复的 workflow 断言**

`TestWorkflowPages` 中 `test_workflow_js_ids_exist` 已被 C1 全站覆盖 → 删除该方法, 保留 patients/AGENT/200 三项 (语义与契约互补, 保留双保险亦可 — 决策: 删除重复项, 注释指向 test_ui_contracts.py)。

- [ ] **Step 5: Commit**

```bash
git add tests/test_ui_contracts.py tests/test_html_pages.py
git commit -m "test: 全站 UI 契约测试 C1-C7 (DOM/JS/API 一致性兜底)"
```

---

### Task 5: AGENTS.md 增补 + 全量验证

**Files:**
- Modify: `AGENTS.md` (质量门禁章节)

**Interfaces:**
- Consumes: Task 1-4 全部产物

- [ ] **Step 1: AGENTS.md 质量门禁章节增补**

在 "## 质量门禁" 代码块后追加:

```markdown
### UI 页面契约 (2026-07-17 起强制)

- 新增/修改 HTML 页面必须通过 `pytest tests/test_ui_contracts.py` (C1-C7: DOM id / onclick / PATIENTS / AGENT / fetch 路由 / workflow tool 契约)
- 数字病人加载必须走 `haip.patients.load_patients()`, 禁止各 UI 自行解析 patients.json
- 渲染函数禁止在循环中复用函数参数名 (ruff PLR1704 强制)
```

- [ ] **Step 2: 全量回归**

Run: `python -m pytest packages/haip-core/tests/ tests/ -q`
Expected: 全部 passed (含 integration; TestDemoPage 6 项既有失败与本次无关, 记录不阻断)

Run: `python -m ruff check packages/haip-core/ tests/; python -m mypy packages/haip-core/haip/`
Expected: 0 errors

- [ ] **Step 3: 手工冒烟**

重启 8769 服务, 浏览器验证 `/workflow/orthopedic-surgery`: 选患者 → 参数联动 → 执行 checklist → status ok。

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "docs: AGENTS.md 增补 UI 契约门禁"
```
