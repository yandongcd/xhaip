"""诊疗流程 UI 渲染器 — 动态阶段 + 角色切换 + 数字病人 (Gold Standard Design System).

每个 Agent 通过 YAML 定义 workflows / roles / stages，
CSS 和 JS 已抽取至 ui_process_css.py / ui_process_js.py。
"""

from __future__ import annotations

import json
from pathlib import Path

from haip.ui_process_css import PROCESS_CSS
from haip.ui_process_js import PROCESS_JS

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PATIENTS_FILE = PROJECT_ROOT / "packages" / "haip-hospital" / "data" / "patients.json"

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
  --bg-default:#ffffff;--bg-overlay:#f6f8fa;--bg-inset:#f0f3f6;
  --bg-subtle:#e8ecf0;--bg-elevated:#ffffff;--border:#d0d7de;
  --border-muted:#e1e5ea;--text:#1f2328;--text2:#656d76;
  --text3:#8b949e;--accent:#0969da;--accent-hover:#0550ae;

  --red:#cf222e;--red-bg:rgba(207,34,46,0.10);
  --blue:#0969da;--blue-bg:rgba(9,105,218,0.10);
  --green:#1a7f37;--green-bg:rgba(26,127,55,0.10);
  --amber:#8b6914;--amber-bg:rgba(139,105,20,0.10);
  --purple:#6e5494;--purple-bg:rgba(110,84,148,0.10);
  --radius:8px;--radius-sm:6px;--radius-full:999px;
  --shadow-sm:0 1px 3px rgba(0,0,0,0.06);
  --shadow-md:0 4px 12px rgba(0,0,0,0.08);
  --fs-sm:12px;--fs-base:14px;--fs-lg:16px;--fs-xl:20px;
  --h:52px;
}}
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
html{{font-size:16px;-webkit-font-smoothing:antialiased}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',Arial,sans-serif;background:var(--bg-default);color:var(--text);min-height:100vh;font-size:14px;line-height:1.47;display:flex;flex-direction:column}}

/* ── Header ── */
.header{{flex-shrink:0;z-index:1000;background:var(--bg-elevated);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 20px;height:var(--h);gap:12px}}
.header-logo{{font-size:16px;font-weight:700;color:var(--accent);cursor:pointer;display:flex;align-items:center;gap:6px}}
.header-logo span{{font-weight:400;font-size:12px;color:var(--text2);margin-left:4px}}
.header-role{{display:flex;gap:4px;margin-left:12px}}
.role-pill{{background:transparent;border:1px solid var(--border);border-radius:var(--radius-full);padding:3px 12px;font-size:12px;cursor:pointer;transition:all .2s;color:var(--text2);font-family:inherit}}
.role-pill:hover{{border-color:var(--accent);color:var(--text)}}
.role-pill.active{{background:var(--accent);border-color:var(--accent);color:#fff}}
.header-patient{{margin-left:auto;font-size:13px;color:var(--text2);display:none;align-items:center;gap:8px}}
.header-patient.visible{{display:flex}}
.header-patient .hp-name{{font-weight:600;color:var(--text)}}
.header-patient .hp-badge{{font-size:10px;padding:1px 8px;border-radius:var(--radius-full);background:var(--blue-bg);color:var(--blue);white-space:nowrap}}

/* ── Hamburger Menu ── */
.menu-overlay{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4);z-index:2000;display:none}}
.menu-overlay.open{{display:block}}
.menu-panel{{position:fixed;top:0;left:0;width:280px;height:100%;background:var(--bg-elevated);border-right:1px solid var(--border);z-index:2001;transform:translateX(-100%);transition:transform .2s ease;display:flex;flex-direction:column}}
.menu-panel.open{{transform:translateX(0)}}
.menu-header{{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid var(--border-muted)}}
.menu-header .close-btn{{width:28px;height:28px;display:flex;align-items:center;justify-content:center;border-radius:var(--radius-sm);cursor:pointer;color:var(--text2);border:none;background:none;font-size:18px;font-family:inherit}}
.menu-header .close-btn:hover{{background:var(--bg-subtle)}}
.menu-items{{flex:1;overflow-y:auto;padding:8px 0}}
.menu-item{{display:flex;align-items:center;gap:10px;padding:9px 16px;cursor:pointer;color:var(--text2);font-size:13px;transition:all .15s;border:none;background:none;width:100%;text-align:left;font-family:inherit}}
.menu-item:hover{{background:var(--bg-subtle);color:var(--text)}}
.menu-item .mi-icon{{font-size:15px;width:22px;text-align:center}}
.menu-item.active{{background:var(--blue-bg);color:var(--blue);border-left:2px solid var(--blue)}}
.menu-divider{{height:1px;background:var(--border-muted);margin:4px 12px}}
.page-panel{{display:none;padding:16px 24px;overflow-y:auto;flex:1}}
.page-panel h2{{font-size:18px;font-weight:600;margin-bottom:12px}}

/* ── 3-Column Layout ── */
.app{{display:flex;flex:1;min-height:0}}
  .leftbar{{width:260px;flex-shrink:0;border-right:1px solid var(--border-muted);background:var(--bg-overlay);display:flex;flex-direction:column;overflow:hidden}}
.lb-search{{padding:10px 12px;border-bottom:1px solid var(--border-muted)}}
.lb-search input{{width:100%;padding:6px 10px;background:var(--bg-elevated);border:1px solid var(--border);border-radius:var(--radius-full);font-size:12px;outline:none;font-family:inherit;color:var(--text)}}
.lb-search input:focus{{border-color:var(--blue)}}
.lb-header{{padding:8px 12px 4px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text3)}}
.patient-list{{flex:1;overflow-y:auto}}
.p-item{{padding:10px 12px;border-bottom:1px solid var(--border-muted);cursor:pointer;transition:all .15s;font-size:13px}}
.p-item:hover{{background:var(--blue-bg)}}
.p-item.active{{background:var(--blue-bg);border-left:3px solid var(--accent)}}
.p-item .p-name{{font-weight:500;display:flex;align-items:center;gap:6px}}
.p-item .p-name .p-age{{font-weight:400;color:var(--text2);font-size:12px}}
.p-item .p-diag{{font-size:11px;color:var(--text2);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.p-item .p-meta{{font-size:10px;color:var(--text3);margin-top:2px;display:flex;align-items:center;gap:6px}}
.p-item .p-stage{{font-size:9px;padding:1px 6px;border-radius:var(--radius-full);font-weight:500}}
.p-stage.urgent{{background:var(--red-bg);color:var(--red)}}
.p-stage.normal{{background:var(--blue-bg);color:var(--blue)}}
.lb-footer{{padding:8px 12px;font-size:10px;color:var(--text3);border-top:1px solid var(--border-muted);text-align:center}}

.center{{flex:1;overflow-y:auto;background:var(--bg-default);padding:20px 24px}}

.rightbar{{width:200px;flex-shrink:0;border-left:1px solid var(--border-muted);background:var(--bg-overlay);display:flex;flex-direction:column;padding:12px}}
.rb-title{{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.3px;color:var(--text3);margin-bottom:8px}}
.rb-list{{flex:1;overflow-y:auto}}
.rb-item{{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:var(--radius-sm);transition:all .15s;font-size:var(--fs-sm);cursor:pointer}}
.rb-item:hover{{background:var(--bg-subtle)}}
.rb-item.active{{background:var(--blue-bg)}}
.rb-item .rb-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;border:2px solid var(--border-muted);transition:all .2s}}
.rb-item .rb-dot.done{{background:var(--green);border-color:var(--green);box-shadow:0 0 0 3px var(--green-bg)}}
.rb-item .rb-dot.current{{background:var(--accent);border-color:var(--accent);box-shadow:0 0 0 3px var(--blue-bg)}}
.rb-item .rb-dot.locked{{border-color:var(--border-muted)}}
.rb-info{{flex:1;min-width:0}}
.rb-item .rb-name{{font-weight:500;font-size:12px}}
.rb-item .rb-status{{font-size:9px;padding:1px 6px;border-radius:var(--radius-full);margin-left:auto}}
.rb-item .rb-status.done{{background:var(--green-bg);color:var(--green)}}
.rb-item .rb-status.active-s{{background:var(--blue-bg);color:var(--blue)}}
.rb-stats{{margin-top:12px;padding-top:8px;border-top:1px solid var(--border-muted)}}

/* ── Stage Content ── */
.stage-content{{display:none;animation:fadeIn .25s ease}}
.stage-content.active{{display:block}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
.stage-hdr{{display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border-muted)}}
.stage-hdr .sh-num{{width:28px;height:28px;border-radius:50%;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;flex-shrink:0}}
.stage-hdr h2{{font-size:var(--fs-lg);font-weight:600;letter-spacing:-.02em}}
.stage-hdr .sh-role{{font-size:var(--fs-sm);color:var(--text3);background:var(--bg-subtle);padding:2px 10px;border-radius:var(--radius-full)}}
.stage-hdr .sh-desc{{font-size:var(--fs-sm);color:var(--text2);margin-top:2px}}

/* ── Cards ── */
.card{{background:var(--bg-elevated);border:1px solid var(--border);border-radius:var(--radius);padding:16px 20px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}}
.card h3{{font-size:13px;font-weight:600;color:var(--text);margin-bottom:8px;display:flex;align-items:center;gap:6px}}
.card h3 .ch-icon{{font-size:16px}}
.card h4{{font-size:13px;font-weight:600;margin-bottom:6px}}

/* ── KPI Grid ── */
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:12px}}
.kpi{{background:var(--bg-subtle);border:1px solid var(--border-muted);border-radius:var(--radius);padding:12px 10px;text-align:center;transition:box-shadow .2s,transform .2s}}
.kpi:hover{{box-shadow:0 4px 12px rgba(0,0,0,.08);transform:translateY(-1px)}}
.kpi .val{{font-size:24px;font-weight:700;display:block;letter-spacing:-.02em;font-variant-numeric:tabular-nums}}
.kpi .val.blue{{color:var(--blue)}}.kpi .val.red{{color:var(--red)}}.kpi .val.green{{color:var(--green)}}.kpi .val.amber{{color:var(--amber)}}
.kpi .lbl{{font-size:10px;color:var(--text3);margin-top:2px;text-transform:uppercase;letter-spacing:.04em}}

/* ── Sections ── */
.section{{margin-bottom:14px}}
.section-title{{font-size:var(--fs-sm);font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2);margin-bottom:8px}}
.summary-bar{{background:var(--bg-overlay);border:1px solid var(--border-muted);border-radius:var(--radius-sm);padding:12px 16px;display:flex;flex-wrap:wrap;gap:4px 12px;font-size:var(--fs-base);line-height:1.7}}
.dp{{display:flex;padding:4px 0;border-bottom:1px solid var(--border-muted);line-height:1.6}}
.dp:last-child{{border-bottom:none}}
.dpl{{width:72px;flex-shrink:0;color:var(--text3);font-size:var(--fs-sm);font-weight:500}}
.dpv{{color:var(--text);font-size:var(--fs-base);font-weight:500}}

/* ── Tabs ── */
.tabs{{display:flex;gap:4px;margin-bottom:10px;flex-wrap:wrap}}
.tab-btn{{background:transparent;border:1px solid var(--border);border-radius:var(--radius-full);padding:4px 14px;font-size:11px;cursor:pointer;transition:all .2s;color:var(--text2);font-family:inherit;white-space:nowrap}}
.tab-btn:hover{{border-color:var(--accent);color:var(--text)}}
.tab-btn.active{{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:500}}
.tab-pane{{display:none;animation:fadeIn .25s ease}}
.tab-pane.active{{display:block}}

/* ── Triage Card ── */
.triage-card{{border-radius:var(--radius);padding:12px 16px;border-left:4px solid var(--blue);background:var(--bg-elevated);border-top:1px solid var(--border);border-right:1px solid var(--border);border-bottom:1px solid var(--border)}}
.triage-card.I{{border-left-color:var(--red);background:var(--red-bg)}}
.triage-card.II{{border-left-color:var(--amber);background:var(--amber-bg)}}
.triage-card.III{{border-left-color:var(--green);background:var(--green-bg)}}
.triage-card.IV{{border-left-color:var(--blue);background:var(--blue-bg)}}
.triage-main{{font-size:18px;font-weight:700}}
.triage-sub{{font-size:12px;color:var(--text2);margin-top:3px}}
.tri-i{{color:var(--red)}}.tri-ii{{color:var(--amber)}}.tri-iii{{color:var(--green)}}.tri-iv{{color:var(--blue)}}

/* ── Tags ── */
.tag{{display:inline-block;padding:2px 8px;border-radius:var(--radius-full);font-size:var(--fs-sm);font-weight:500}}
.tag.blue{{background:var(--blue-bg);color:var(--blue)}}
.tag.red{{background:var(--red-bg);color:var(--red)}}
.tag.green{{background:var(--green-bg);color:var(--green)}}
.tag.amber{{background:var(--amber-bg);color:var(--amber)}}
.tag.purple{{background:var(--purple-bg);color:var(--purple)}}

/* ── Alerts ── */
.alert{{border-radius:var(--radius);padding:10px 14px;font-size:12px;line-height:1.5;margin-top:6px}}
.alert.red{{background:var(--red-bg);border:1px solid rgba(207,34,46,.25);color:var(--red)}}
.alert.blue{{background:var(--blue-bg);border:1px solid rgba(9,105,218,.25);color:var(--blue)}}
.alert.green{{background:var(--green-bg);border:1px solid rgba(26,127,55,.25);color:var(--green)}}
.alert.amber{{background:var(--amber-bg);border:1px solid rgba(139,105,20,.25);color:var(--amber)}}

/* ── Buttons ── */
.btn{{background:var(--accent);color:#fff;border:none;border-radius:var(--radius-full);padding:6px 16px;font-size:12px;font-weight:500;cursor:pointer;transition:all .15s;font-family:inherit;display:inline-flex;align-items:center;gap:4px}}
.btn:hover{{background:var(--accent-hover);box-shadow:0 4px 12px rgba(9,105,218,.25)}}
.btn:active{{transform:scale(.96)}}
.btn-outline{{background:transparent;border:1px solid var(--border);color:var(--text)}}
.btn-outline:hover{{background:var(--bg-subtle)}}
.btn-sm{{padding:4px 12px;font-size:11px}}
.btn-success{{background:var(--green);color:#fff}}
.fx-nav{{display:flex;justify-content:space-between;margin-top:16px;padding-top:12px;border-top:1px solid var(--border-muted)}}

/* ── Table ── */
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:var(--bg-overlay);padding:8px 10px;text-align:left;font-weight:500;color:var(--text2);border-bottom:1px solid var(--border);text-transform:uppercase;letter-spacing:.03em;font-size:11px}}
td{{padding:6px 10px;border-bottom:1px solid var(--border-muted)}}
tr:hover td{{background:var(--bg-overlay)}}

/* ── Checklist ── */
.cl-section{{margin-bottom:12px}}
.cl-section-title{{font-size:var(--fs-sm);font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.3px;margin-bottom:6px;padding-bottom:4px;border-bottom:1px solid var(--border-muted)}}
.cl-item{{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:var(--radius-sm);font-size:var(--fs-base);border-bottom:1px solid var(--border-muted)}}
.cl-item:last-child{{border-bottom:none}}
.cl-item .ck{{width:16px;height:16px;border-radius:3px;border:2px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:10px;flex-shrink:0}}
.cl-item .ck.done{{background:var(--green);border-color:var(--green);color:#fff}}
.cl-item .cl-name{{font-weight:500;flex-shrink:0;min-width:90px}}
.cl-item .cl-dept{{font-size:10px;padding:1px 6px;border-radius:var(--radius-full);background:var(--blue-bg);color:var(--blue);margin-left:4px}}
.cl-item .cl-reason{{font-size:11px;color:var(--text3);margin-left:auto}}

/* ── Stage Bar ── */
.stage-bar{{height:3px;background:var(--accent);border-radius:2px;margin-bottom:16px;opacity:.3;transition:all .3s;width:0%}}
.stage-bar.s1{{background:var(--blue)}}.stage-bar.s2{{background:var(--green)}}
.stage-bar.s3{{background:var(--amber)}}.stage-bar.s4{{background:var(--red)}}
.stage-bar.s5{{background:var(--purple)}}.stage-bar.s6{{background:var(--blue)}}
.stage-bar.s7{{background:var(--green)}}.stage-bar.s8{{background:var(--red)}}

/* ── Followup Timeline ── */
.fu-timeline{{display:flex;justify-content:space-between;align-items:flex-start;position:relative;padding:12px 0;margin:8px 0}}
.fu-timeline::before{{content:'';position:absolute;top:10px;left:40px;right:40px;height:2px;background:var(--border)}}
.fu-node{{display:flex;flex-direction:column;align-items:center;gap:4px;position:relative;z-index:1;flex:1;text-align:center}}
.fu-dot{{width:14px;height:14px;border-radius:50%;background:var(--accent);border:3px solid var(--bg-elevated);box-shadow:0 0 0 2px var(--accent);flex-shrink:0}}
.fu-label{{font-size:13px;font-weight:600;color:var(--text)}}
.fu-sub{{font-size:10px;color:var(--text2)}}

/* ── Empty / Loading ── */
.empty{{text-align:center;padding:60px 20px;color:var(--text3)}}
.empty .e-icon{{font-size:48px;margin-bottom:12px}}
.empty .e-text{{font-size:14px;margin-bottom:4px}}
.empty .e-sub{{font-size:12px}}
.loading{{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--text2)}}
.loading::before{{content:'';width:12px;height:12px;border:2px solid var(--border-muted);border-top-color:var(--accent);border-radius:50%;animation:spin .6s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}

/* ── Toast ── */
.toast{{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:var(--text);color:var(--bg-default);padding:8px 20px;border-radius:var(--radius-full);font-size:13px;z-index:9999;box-shadow:0 4px 20px rgba(0,0,0,.2);display:none}}

/* ── Scrollbar ── */
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:transparent}}::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}

/* ── Responsive ── */
@media(max-width:900px){{.leftbar,.rightbar{{display:none}}.center{{width:100%}}.header{{flex-wrap:wrap;height:auto;padding:6px 10px}}.header-role{{margin-left:0;margin-top:4px}}}}
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
{PROCESS_JS}
</script>
</body>
</html>"""


def _load_patients(agent_name: str) -> list[dict]:
    """从 patients.json 加载与给定 agent 兼容的患者数据。"""
    try:
        with open(PATIENTS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return _fallback_patients()

    all_patients = data.get("patients", []) if isinstance(data, dict) else data
    if isinstance(all_patients, list):
        matched = [p for p in all_patients
                   if agent_name in p.get("compatible_agents", [])]
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
