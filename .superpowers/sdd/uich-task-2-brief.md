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



---

## Global Constraints

- ruff line-length=100, `ignore=["E402"]` 保持不变, 新增 `extend-select=["PLR1704"]`
- mypy strict=false, 修改文件必须 0 错误
- 不引入新第三方依赖
- 不修改 ui_render.py / ui_ortho*.html / ui_pharmacy*.html 的实现 (契约测试兜底)
- 所有命令在 `D:\FC\xhaip` 执行

---

