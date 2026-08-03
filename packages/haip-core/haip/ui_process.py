"""诊疗流程 UI 渲染器 — 动态阶段 + 角色切换 + 数字病人.

CSS 和 JS 已迁移至 haip/static/ 独立文件，不再嵌入 Python。
"""

from __future__ import annotations

import json


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
    if roles is None:
        roles = []
    if stages is None:
        stages = []
    if guard_triggers is None:
        guard_triggers = []

    patients = _load_patients(name)

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

    # ── 数据注入 (JSON → JS 全局变量) ──
    xhaip_data = json.dumps({
        "stages": stages,
        "guard_triggers": guard_triggers,
        "depends_on": depends_on or [],
        "name": name,
        "cn_name": cn_name,
        "agent_type": agent_type,
        "department": department or "—",
        "default_role_id": roles[0]["id"] if roles else "attending",
    }, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{cn_name} · 诊疗流程 — HAIP</title>
<link rel="stylesheet" href="/static/process.css">
</head>
<body>

<!-- ─── Hamburger Menu ─── -->
<div class="menu-overlay" id="menu-overlay" onclick="closeMenu()"></div>
<div class="menu-panel" id="menu-panel">
  <div class="menu-header">
    <button class="close-btn" onclick="closeMenu()">×</button>
    <span style="font-weight:600;font-size:14px">{cn_name}</span>
  </div>
  <div class="menu-items">
    <button class="menu-item" onclick="switchToPage('home')"><span class="mi-icon">🏠</span> 首页</button>
    <button class="menu-item" onclick="switchToPage('haip-instance')"><span class="mi-icon">🔄</span> HAIP 实例 — 多智能体协同</button>
    <button class="menu-item" onclick="switchToPage('guidelines')"><span class="mi-icon">📚</span> 指南资产</button>
    <div class="menu-divider"></div>
    <button class="menu-item" onclick="switchToPage('help')"><span class="mi-icon">❓</span> 帮助</button>
  </div>
</div>

<!-- ─── Header ─── -->
<div class="header">
  <div class="header-logo" onclick="toggleMenu()">
    <span style="font-size:20px">🏥</span> {cn_name} · HAIP
  </div>
  <div class="header-role">
{role_html}
  </div>
  <div class="header-patient" id="header-patient">
    <span class="hp-name" id="hp-name"></span>
    <span class="hp-badge" id="hp-badge"></span>
  </div>
</div>

<!-- ─── 3-Column Layout ─── -->
<div class="app">
  <!-- Left: Patient List -->
  <div class="leftbar">
    <div class="lb-search">
      <input type="text" placeholder="搜索患者..." oninput="searchPatients()" id="patient-search">
    </div>
    <div class="lb-header">数字病人 · {cn_name}</div>
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

<!-- ─── Data Injection ─── -->
<script type="application/json" id="xhaip-data">
{xhaip_data}
</script>

<!-- ─── Logic ─── -->
<script src="/static/process.js"></script>
</body>
</html>"""


def _load_patients(agent_name: str) -> list[dict]:
    from haip.patients import load_patients
    matched = load_patients(agent_name, limit=30, only_compatible=True)
    if matched:
        return _normalize_patients(matched)
    return _fallback_patients()


def _normalize_patients(patients: list[dict]) -> list[dict]:
    result = []
    for p in patients[:30]:
        result.append({
            "patient_id": p.get("patient_id", p.get("id", "")),
            "name": p.get("name", p.get("patient_name", "")),
            "age": p.get("age", p.get("age_years", "")),
            "gender": p.get("gender", p.get("sex", "")),
            "diagnosis": p.get("diagnosis", p.get("primary_diagnosis", "")),
            "department": p.get("department", p.get("dept", "")),
            "scenario": p.get("scenario", p.get("clinical_scenario", "")),
            "urgency": p.get("urgency", "normal"),
            "lab_results": p.get("lab_results", {}),
            "present": p.get("present", p.get("history_of_present_illness", "")),
            "plan": p.get("plan", ""),
            "execution": p.get("execution", ""),
            "followup": p.get("followup", ""),
            "assessments": p.get("assessments", []),
            "tools": p.get("tools", []),
        })
    return result


def _fallback_patients() -> list[dict]:
    return [
        {"patient_id": "P000", "name": "示例患者", "age": "55", "gender": "M",
         "diagnosis": "示例诊断", "department": "示例科室", "scenario": "示例场景",
         "lab_results": {"WBC": "6.5", "HGB": "140"}, "urgency": "normal"},
    ]
