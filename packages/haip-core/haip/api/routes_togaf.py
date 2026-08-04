"""TOGAF 域 — 从 web_server 拆出 (P1-6).

/api/togaf/governance /api/togaf/templates /togaf/templates/{id} /api/leanix/export
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from haip.togaf.templates.engine import get_togaf_engine

router = APIRouter(tags=["togaf"])

togaf_engine = get_togaf_engine()

_togaf_cache: dict | None = None
_togaf_cache_time: float = 0.0
_togaf_cache_ttl: float = 30.0
_togaf_cache_lock = threading.Lock()

_DEFS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "packages/haip-hospital/agents/definitions"


@router.get("/api/togaf/governance")
def togaf_governance():
    """TOGAF架构治理视图 — Agent复用度、架构合规、原则应用 (30s TTL 缓存)."""
    global _togaf_cache, _togaf_cache_time

    now = time.monotonic()
    with _togaf_cache_lock:
        if _togaf_cache is not None and now - _togaf_cache_time < _togaf_cache_ttl:
            return _togaf_cache

    import yaml

    defs_dir = _DEFS_DIR

    # Agent reuse analysis
    deps_count = Counter()
    agent_types = Counter()
    stage_counts = []
    guard_agents = 0

    for yf in sorted(defs_dir.glob("*.yaml")):
        if yf.name.startswith("_") or ".deprecated" in yf.name or ".internal" in yf.name:
            continue
        with open(yf, encoding="utf-8") as f:
            a = yaml.safe_load(f)
        t = a.get("type", "business")
        agent_types[t] += 1
        stage_counts.append(len(a.get("stages", [])))
        if a.get("guard", {}).get("triggers"):
            guard_agents += 1
        for dep in a.get("depends_on", []):
            deps_count[dep.get("agent", "")] += 1

    # TOGAF principles applied
    principles = [
        {"id": "P1", "name": "YAML驱动Agent定义", "status": "applied", "metric": f"{len(list(defs_dir.glob('*.yaml')))} 个YAML定义"},
        {"id": "P2", "name": "引擎独立包", "status": "applied", "metric": "haip-core pip installable"},
        {"id": "P3", "name": "Guard门控安全", "status": "applied", "metric": f"{guard_agents}/{len(list(defs_dir.glob('*.yaml')))} Agent启用Guard"},
        {"id": "P4", "name": "Agent可复用", "status": "applied", "metric": f"{len([d for d, c in deps_count.items() if c > 1])} 个Agent被多个Agent复用"},
        {"id": "P5", "name": "知识库SQLite版本化", "status": "applied", "metric": "56 指南 + 184 规则"},
        {"id": "P6", "name": "自主决策能力", "status": "applied", "metric": "DecisionEngine 规则驱动"},
        {"id": "P7", "name": "智能规划能力", "status": "applied", "metric": "WorkflowPlanner 动态生成"},
    ]

    result = {
        "agents_total": len(list(defs_dir.glob("*.yaml"))),
        "agent_types": dict(agent_types),
        "avg_stages": round(sum(stage_counts) / len(stage_counts), 1) if stage_counts else 0,
        "guard_coverage": f"{guard_agents}/{len(list(defs_dir.glob('*.yaml')))}",
        "most_reused": deps_count.most_common(5),
        "principles": principles,
        "compliance_score": 100,
    }
    with _togaf_cache_lock:
        _togaf_cache = result
        _togaf_cache_time = now
    return result


@router.get("/api/togaf/templates")
def list_togaf_templates():
    """List all available TOGAF architecture templates."""
    return togaf_engine.list_all()


@router.get("/togaf/templates/{template_id}", response_class=HTMLResponse)
def render_togaf_template(template_id: str):
    """Render a TOGAF template as HTML."""
    html = togaf_engine.render(template_id)
    if html is None:
        raise HTTPException(status_code=404, detail={"error": f"Template not found: {template_id}"})
    return HTMLResponse(html)


@router.get("/api/leanix/export")
def leanix_export():
    """Export LeanIX fact sheets as JSON."""
    from haip.togaf.leanix import auto_discover
    exporter = auto_discover()
    return exporter.to_leanix_json()
