"""诊疗流程 UI 渲染器 — 动态阶段 + 角色切换 + 数字病人 (Gold Standard Design System).

每个 Agent 通过 YAML 定义 workflows / roles / stages，
CSS 和 JS 已抽取至 ui_process_css.py / ui_process_js.py。
"""

from __future__ import annotations

import json

from haip.ui_process_css import PROCESS_CSS
from haip.ui_process_js import PROCESS_JS

STAGE_COLORS = ["#0969da", "#1a7f37", "#8b6914", "#cf222e", "#6e5494", "#0a84ff",
                "#1a7f37", "#cf222e", "#0969da"]


def render_process_ui(
    name: str,
    cn_name: str,
    department: str = "",
    agent_type: str = "business",
    roles: list[dict] | None = None,
    stages: list[dict] | None = None,
    guard_triggers: list[str] | None = None,
    depends_on: list[dict] | None = None,
) -> str:
    """渲染诊疗流程 HTML — Core.

    Args:
        name: Agent 技术名 (e.g. orthopedic-surgery)
        cn_name: 中文名 (e.g. 创伤骨科智能体)
        department: 科室名
        agent_type: business / specialist / master_data
        roles: 角色列表 [{"id":"attending","label":"主治医师","icon":"🩺"}, ...]
        stages: 阶段列表 [{"order":1,"id":"reg","label":"登记与初评","desc":"...","role":"主治"}, ...]
        guard_triggers: 高危触发标签
        depends_on: 依赖的其他 Agent 列表
    """
    if roles is None:
        roles = []
    if stages is None:
        stages = []
    if guard_triggers is None:
        guard_triggers = []

    patients = _load_patients(name)
    stages_json = json.dumps(stages, ensure_ascii=False)
    patients_json = json.dumps(patients, ensure_ascii=False)

    # ── 角色 Pill HTML ──
    role_html = ""
    for i, r in enumerate(roles):
        icon = r.get("icon", "")
        label = r.get("label", r.get("id", ""))
        cls = ' active' if i == 0 else ''
        rid = r["id"].replace("'", "\\'")
        role_html += '<button class="role-pill' + cls + '" data-role="' + r["id"] + '" onclick="switchRole(\'' + rid + '\')">' + icon + ' ' + label + '</button>\n'

    # ── 阶段导航 HTML ──
    sb_items = ""
    for i, s in enumerate(stages):
        cls = ' active' if i == 0 else ''
        sb_items += (
            f'<div class="rb-item{cls}" data-stage="{s["order"]}" onclick="clickStage({s["order"]})">'
            f'<span class="rb-dot current"></span>'
            f'<div class="rb-info"><div class="rb-name">{s["order"]}. {s["label"]}</div></div>'
            f'<span class="rb-status active-s">当前</span>'
            f'</div>\n'
        )

    # ── 阶段面板 ──
    panels = ""
    for s in stages:
        act = ' active' if s["order"] == 1 else ''
        panels += f'<div class="stage-content{act}" id="stage-{s["order"]}"></div>\n'

    # ── Guard 标签 ──
    guard_html = ""
    if guard_triggers:
        tags = " ".join(f'<span class="tag red">{t}</span>' for t in guard_triggers)
        guard_html = (
            '<div class="rb-stats"><div class="rb-stat"><span>高危触发</span></div>'
            f'<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:3px">{tags}</div></div>'
        )

    # ── 依赖 Agent 列表 ──
    deps_html = ""
    if depends_on:
        deps = " · ".join(d.get("reason", d.get("agent", "")) for d in depends_on[:5])
        deps_html = (
            '<div class="rb-stats"><div class="rb-stat"><span>协作 Agent</span></div>'
            f'<div style="font-size:10px;color:var(--text3);margin-top:4px">{deps}</div></div>'
        )

    # Resolve JS variables (extracted to ui_process_js.py, needs format)
    import json as _json
    resolved_js = PROCESS_JS.format(
        patients_json=patients_json,
        stages_json=stages_json,
        guard_triggers_json=_json.dumps(guard_triggers, ensure_ascii=False),
        depends_on_json=_json.dumps(depends_on or [], ensure_ascii=False),
        name=name, cn_name=cn_name, agent_type=agent_type,
        department=department or '—',
        default_role_id=roles[0]['id'] if roles else 'attending',
        roles_count=str(len(roles)),
        stages_count=str(len(stages)),
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{cn_name} · 诊疗流程 — HAIP</title>
<style>
{PROCESS_CSS}
</style>
</head>
<body>

<!-- ─── Hamburger Menu ─── -->
<div class="menu-overlay" id="menu-overlay" onclick="closeMenu()"></div>
<div class="menu-panel" id="menu-panel">
  <div class="menu-header">
    <button class="close-btn" onclick="closeMenu()">&times;</button>
    <h3 style="font-size:14px;font-weight:600">{department or cn_name}</h3>
  </div>
  <div class="menu-items">
    <button class="menu-item active" onclick="switchToPage('home')"><span class="mi-icon">🏠</span> 首页</button>
    <button class="menu-item" onclick="switchToPage('haip-instance')"><span class="mi-icon">🔄</span> HAIP 实例 — 多智能体协同</button>
    <button class="menu-item" onclick="switchToPage('guidelines')"><span class="mi-icon">📚</span> 指南资产</button>
    <div class="menu-divider"></div>
    <button class="menu-item" onclick="switchToPage('help')"><span class="mi-icon">❓</span> 帮助</button>
  </div>
</div>

<!-- ─── Header ─── -->
<div class="header">
  <div class="header-logo" onclick="toggleMenu()">{department or '🏥'} <span>· HAIP</span></div>
  <div class="header-role" id="role-bar">
    {role_html}
  </div>
  <div class="header-patient" id="header-patient">
    <span class="hp-name" id="hp-name"></span>
    <span class="hp-badge" id="hp-stage"></span>
  </div>
</div>

<!-- ─── 3-Column Layout ─── -->
<div class="app">
  <div class="leftbar">
    <div class="lb-search"><input type="text" id="patient-search" placeholder="搜索患者..." oninput="searchPatients()"></div>
    <div class="lb-header">数字病人 · {department or cn_name}</div>
    <div class="patient-list" id="patient-list"></div>
    <div class="lb-footer">共 <strong id="lb-count">0</strong> 位患者</div>
  </div>

  <div class="center" id="center-content">
{panels}
    <!-- ── Page Panels (Hamburger) ── -->
    <div class="page-panel" id="page-home">
      <h2>🏠 {cn_name} — 诊疗流程</h2>
      <div class="kpis">
        <div class="kpi"><span class="val blue" id="home-stages">0</span><span class="lbl">诊疗阶段</span></div>
        <div class="kpi"><span class="val blue" id="home-patients">0</span><span class="lbl">数字病人</span></div>
        <div class="kpi"><span class="val blue" id="home-roles">0</span><span class="lbl">智能体角色</span></div>
        <div class="kpi"><span class="val blue" id="home-guards">0</span><span class="lbl">安全触发</span></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:4px">
        <div class="card" style="cursor:pointer" onclick="switchToPage('haip-instance')"><h3>🔄 HAIP 实例</h3><div style="font-size:12px;color:var(--text2)">多智能体协同拓扑</div></div>
        <div class="card" style="cursor:pointer" onclick="switchToPage('guidelines')"><h3>📚 指南资产</h3><div style="font-size:12px;color:var(--text2)">已注册临床指南</div></div>
        <div class="card" style="cursor:pointer" onclick="closeMenu();clickStage(1)"><h3>🔄 返回流程</h3><div style="font-size:12px;color:var(--text2)">继续诊疗流程</div></div>
        <div class="card" style="cursor:pointer" onclick="resetSelection()"><h3>🔄 重置患者</h3><div style="font-size:12px;color:var(--text2)">清除当前选择</div></div>
      </div>
    </div>

    <div class="page-panel" id="page-haip-instance">
      <h2>🔄 HAIP 实例 — {department or cn_name} 多智能体协同</h2>
      <div style="font-size:12px;color:var(--text2);margin-bottom:12px">TOGAF 10 实例化架构</div>
      <div class="card">
        <h3>依赖智能体</h3>
        <div id="deps-list" style="font-size:13px;line-height:1.8;color:var(--text)"></div>
      </div>
      <div class="card"><h3>📊 患者覆盖</h3>
        <table><tr><th>科室</th><th>患者数</th><th>场景</th></tr>
        <tbody id="coverage-table"></tbody></table>
      </div>
    </div>

    <div class="page-panel" id="page-guidelines">
      <h2>📚 指南资产</h2>
      <div style="font-size:12px;color:var(--text2);margin-bottom:12px">临床路径和诊疗规范</div>
      <div class="card"><h3>👮 高危触发规则</h3>
        <div id="guidelines-triggers" style="font-size:13px;line-height:1.8;display:flex;flex-wrap:wrap;gap:6px"></div>
      </div>
      <div class="card"><h3>📋 诊疗阶段</h3>
        <div id="guidelines-stages" style="font-size:13px;line-height:1.8"></div>
      </div>
    </div>

    <div class="page-panel" id="page-help">
      <h2>❓ 操作指南</h2>
      <div class="card"><h3>基本操作</h3>
        <div style="font-size:13px;line-height:1.8;color:var(--text2)">
          <p>1. 左侧列表选择数字病人</p>
          <p>2. 按诊疗阶段逐步推进: 登记→诊断→评估→方案→执行→随访</p>
          <p>3. 点击「确认」进入下一阶段</p>
          <p>4. 点击 Header Logo 打开菜单（Home / HAIP实例 / 指南 / 帮助）</p>
          <p>5. 角色 Pill 切换不同视角</p>
        </div>
      </div>
      <div class="card"><h3>Agent 信息</h3>
        <div style="font-size:13px;line-height:1.8">
          <div class="dp"><span class="dpl">Agent</span><span class="dpv">{name}</span></div>
          <div class="dp"><span class="dpl">类型</span><span class="dpv"><span class="tag blue">{agent_type}</span></span></div>
          <div class="dp"><span class="dpl">科室</span><span class="dpv">{department or '—'}</span></div>
          <div class="dp"><span class="dpl">阶段数</span><span class="dpv">{len(stages)}</span></div>
        </div>
      </div>
    </div>
  </div>

  <div class="rightbar">
    <div class="rb-title">诊疗阶段</div>
    <div class="rb-list" id="rb-stages">
{sb_items}
    </div>
    <div class="rb-stats">
      <div class="rb-stat"><span>当前阶段</span><span class="val" id="rb-current-stage" style="font-weight:600">1/{len(stages)}</span></div>
      <div class="rb-stat"><span>已完成</span><span class="val" id="rb-done-count" style="font-weight:600">0</span></div>
    </div>
{guard_html}
{deps_html}
  </div>
</div>

<!-- ─── Toast ─── -->
<div class="toast" id="toast"></div>

<script>
{resolved_js}
</script>
</body>
</html>"""


def _load_patients(agent_name: str) -> list[dict]:
    """从 patients.json 加载与给定 agent 兼容的患者数据。"""
    from haip.patients import load_patients

    matched = load_patients(agent_name, limit=30, only_compatible=True)
    if matched:
        return _normalize_patients(matched)
    return _fallback_patients()


def _normalize_patients(patients: list[dict]) -> list[dict]:
    """标准化患者数据字段名，确保模板 JS 能正确消费。"""
    out = []
    for p in patients[:30]:
        age_val = p.get("age", 0) or p.get("age_months", 0)
        out.append({
            "patient_id": p.get("patient_id", ""),
            "name": p.get("name", "未知"),
            "age": age_val,
            "gender": p.get("gender", ""),
            "diagnosis": p.get("diagnosis", ""),
            "department": p.get("department", ""),
            "scenario": p.get("scenario", ""),
            "lab_results": p.get("lab_results", {}),
            "present": p.get("scenario", ""),
            "urgency": p.get("urgency", "normal"),
            "assessments": p.get("assessments", []),
            "plan": p.get("plan", ""),
            "execution": p.get("execution", ""),
            "followup": p.get("followup", ""),
        })
    return out


def _fallback_patients() -> list[dict]:
    """无患者数据时提供示例数据。"""
    return [
        {"patient_id": "DEMO-001", "name": "示例患者A", "age": 65,
         "diagnosis": "示例诊断 (请配置患者数据)", "department": "默认科室",
         "scenario": "示例临床场景", "lab_results": {"Hb": 130, "WBC": 8.0},
         "urgency": "normal"},
        {"patient_id": "DEMO-002", "name": "示例患者B", "age": 72,
         "diagnosis": "示例诊断 (请配置患者数据)", "department": "默认科室",
         "scenario": "示例临床场景", "lab_results": {"Hb": 115, "WBC": 9.5},
         "urgency": "high"},
    ]


def load_patients_for_agent(agent_name: str) -> list[dict]:
    """公共 API：加载与指定 agent 兼容的患者。"""
    return _load_patients(agent_name)
