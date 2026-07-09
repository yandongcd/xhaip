"""TOGAF Architecture Dashboard — Full Hospital 4A Landscape.

Server-rendered visualization with:
  - 39 dept maturity heatmap (grouped by type)
  - Audit stats (nodes, edges, agents)
  - Dept × Agent mapping table
  - Quick validation status
"""

from __future__ import annotations


def _load_analysis_data() -> dict:
    try:
        from haip.agent import _registry
        from haip.togaf.analysis import analyze_all_v2
        # If registry is empty, try loading from default location
        if not _registry:
            from haip.agent import load_from_dir
            from pathlib import Path
            yaml_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "packages" / "haip-hospital" / "agents" / "definitions"
            if yaml_dir.exists():
                load_from_dir(str(yaml_dir))
        results = analyze_all_v2()
        depts = []
        for r in results:
            depts.append({
                "name": r.org_name,
                "type": r.template_type,
                "score": r.score.total,
                "tier": r.score.tier,
                "has_agent": r.has_agent,
                "agent": r.agent_name,
                "stages": r.stage_count,
                "roles": r.role_count,
                "guideline": r.has_guideline,
                "validation_passed": r.validation_passed,
                "gaps": r.gaps,
            })
        tiers = {"L3 成熟": 0, "L2 发展中": 0, "L1 起步": 0, "L0 未覆盖": 0}
        for d in depts:
            tiers[d["tier"]] = tiers.get(d["tier"], 0) + 1
        avg = sum(d["score"] for d in depts) // max(len(depts), 1)
        return {
            "depts": depts,
            "tiers": tiers,
            "avg_score": avg,
            "total": len(depts),
        }
    except Exception as e:
        return {"error": str(e), "depts": [], "tiers": {}, "avg_score": 0, "total": 0}


def render_dashboard() -> str:
    """Render the TOGAF architecture dashboard HTML page."""
    data = _load_analysis_data()
    depts = data.get("depts", [])
    tiers = data.get("tiers", {})
    avg = data.get("avg_score", 0)
    total = data.get("total", 0)

    # Group departments by type
    groups: dict[str, list[dict]] = {}
    for d in depts:
        groups.setdefault(d["type"], []).append(d)

    # Build heatmap cards HTML
    cards = ""
    for type_name, type_depts in sorted(groups.items()):
        cards += f'<div class="group-section"><div class="group-title">{type_name} ({len(type_depts)} 科室)</div><div class="dept-grid">'
        for d in sorted(type_depts, key=lambda x: -x["score"]):
            color = "#34c759" if d["score"] >= 80 else "#ff9f0a" if d["score"] >= 50 else "#ff453a" if d["score"] >= 20 else "#38383a"
            agent_badge = '<span class="agent-badge">✓</span>' if d["has_agent"] else ""
            guideline_badge = '<span class="guideline-badge">📋</span>' if d["guideline"] else ""
            cards += f"""<div class="dept-card" style="border-left:3px solid {color}">
              <div class="dept-name">{agent_badge}{d["name"]}</div>
              <div class="dept-score" style="color:{color}">{d["score"]}</div>
              <div class="dept-meta">{d["stages"]}阶段 · {d["roles"]}角色 {guideline_badge}</div>
            </div>"""
        cards += "</div></div>"

    # Validation table
    val_rows = ""
    for d in sorted(depts, key=lambda x: -x["score"]):
        status = "✅" if d["validation_passed"] else "—"
        agent = d["agent"] if d["has_agent"] else "—"
        gaps = ", ".join(d.get("gaps", [])[:2]) if d.get("gaps") else ""
        val_rows += f"""<tr>
            <td>{d["name"]}</td><td>{d["type"]}</td><td>{d["score"]}</td>
            <td>{d["stages"]}</td><td>{d["roles"]}</td>
            <td>{agent}</td><td>{status}</td><td style="font-size:10px">{gaps}</td>
          </tr>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>TOGAF 10 架构治理仪表盘 · 南方医院</title>
<style>
:root{{--bg:#1c1c1e;--card-bg:#2c2c2e;--text:#f5f5f7;--text-secondary:#a1a1a6;
  --accent:#0a84ff;--green:#30d158;--amber:#ff9f0a;--red:#ff453a;
  --border:#38383a;--radius:8px}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;line-height:1.47}}
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}

.header{{background:var(--card-bg);border-bottom:1px solid var(--border);
  padding:16px 24px;display:flex;justify-content:space-between;align-items:center}}
.header h1{{font-size:18px;font-weight:600}}
.stats{{display:flex;gap:20px}}
.stat{{text-align:center}}.stat .val{{font-size:24px;font-weight:700;display:block}}
.stat .lbl{{font-size:10px;color:var(--text-secondary);text-transform:uppercase}}

.content{{max-width:1400px;margin:0 auto;padding:20px 24px}}

/* Tier bar */
.tier-bar{{display:flex;height:8px;border-radius:4px;overflow:hidden;margin:16px 0}}
.tier-bar div{{transition:width .5s ease}}
.tier-l3{{background:var(--green)}}.tier-l2{{background:var(--amber)}}
.tier-l1{{background:var(--red)}}.tier-l0{{background:var(--border)}}

/* Heatmap */
.group-section{{margin-bottom:24px}}
.group-title{{font-size:13px;font-weight:600;color:var(--text-secondary);
  margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px}}
.dept-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px}}
.dept-card{{background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);
  padding:10px 14px;transition:all .15s}}
.dept-card:hover{{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.3)}}
.dept-name{{font-size:13px;font-weight:600;display:flex;align-items:center;gap:4px}}
.dept-score{{font-size:28px;font-weight:700;margin:4px 0}}
.dept-meta{{font-size:10px;color:var(--text-secondary)}}
.agent-badge{{font-size:9px;padding:1px 4px;border-radius:3px;background:var(--green);color:#000;font-weight:700}}
.guideline-badge{{font-size:11px}}

/* Table */
table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:16px}}
th{{background:var(--card-bg);padding:8px 10px;text-align:left;font-weight:500;
  color:var(--text-secondary);border-bottom:2px solid var(--border);font-size:11px;text-transform:uppercase}}
td{{padding:6px 10px;border-bottom:1px solid var(--border)}}
tr:hover td{{background:var(--card-bg)}}

.legend{{display:flex;gap:16px;margin:12px 0;font-size:11px;color:var(--text-secondary)}}
.legend span{{display:flex;align-items:center;gap:4px}}
.legend .dot{{width:10px;height:10px;border-radius:2px}}
</style>
</head>
<body>
<div class="header">
  <h1>🏗️ TOGAF 10 架构治理仪表盘 · 南方医院</h1>
  <div class="stats">
    <div class="stat"><span class="val" style="color:var(--green)">{tiers.get('L3 成熟', 0)}</span><span class="lbl">L3 成熟</span></div>
    <div class="stat"><span class="val" style="color:var(--amber)">{tiers.get('L2 发展中', 0)}</span><span class="lbl">L2 发展中</span></div>
    <div class="stat"><span class="val" style="color:var(--red)">{tiers.get('L1 起步', 0)}</span><span class="lbl">L1 起步</span></div>
    <div class="stat"><span class="val">{total}</span><span class="lbl">总科室</span></div>
    <div class="stat"><span class="val" style="color:var(--accent)">{avg}</span><span class="lbl">均分</span></div>
  </div>
</div>

<div class="content">
  <div class="tier-bar">
    <div class="tier-l3" style="width:{tiers.get('L3 成熟', 0)/total*100:.0f}%"></div>
    <div class="tier-l2" style="width:{tiers.get('L2 发展中', 0)/total*100:.0f}%"></div>
    <div class="tier-l1" style="width:{tiers.get('L1 起步', 0)/total*100:.0f}%"></div>
    <div class="tier-l0" style="flex:1"></div>
  </div>

  <div class="legend">
    <span><span class="dot" style="background:var(--green)"></span> L3 成熟 ≥80</span>
    <span><span class="dot" style="background:var(--amber)"></span> L2 发展中 50-79</span>
    <span><span class="dot" style="background:var(--red)"></span> L1 起步 20-49</span>
    <span><span class="dot" style="background:var(--border)"></span> L0 未覆盖 <20</span>
  </div>

  <h2 style="font-size:16px;margin-bottom:12px">科室成熟度热力图</h2>
  {cards}

  <h2 style="font-size:16px;margin:24px 0 12px">科室 × Agent 明细表</h2>
  <div style="overflow-x:auto">
  <table>
    <thead><tr><th>科室</th><th>类型</th><th>评分</th><th>阶段</th><th>角色</th><th>Agent</th><th>校验</th><th>Gap</th></tr></thead>
    <tbody>{val_rows}</tbody>
  </table>
  </div>
</div>
</body>
</html>"""


def render_dashboard_json() -> dict:
    """Return dashboard data as JSON."""
    return _load_analysis_data()
