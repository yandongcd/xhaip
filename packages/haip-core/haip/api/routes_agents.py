"""Agent 信息与患者列表 API — 从 web_server 拆出 (P1-6)."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from haip.agent import _registry
from haip.agent import get as get_agent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agents"])

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


@router.get("/api/patients/{agent_name}")
def get_patients(agent_name: str, limit: int = 50, offset: int = 0):
    """Async patient loading with pagination — 使用共享 mtime 缓存."""
    from haip.patients import load_all_patients

    patients = load_all_patients()
    # Filter compatible patients
    compatible = []
    for p in patients:
        compat = p.get("compatible_agents", [])
        dept = p.get("department", "")
        if not compat or agent_name in compat or \
           agent_name.replace("-", "") in dept.replace(" ", "").lower():
            compatible.append({
                "patient_id": p.get("patient_id", ""),
                "name": p.get("name", p.get("patient_name", "")),
                "age": p.get("age", p.get("age_years", "")),
                "gender": p.get("gender", p.get("sex", "")),
                "diagnosis": p.get("diagnosis", p.get("primary_diagnosis", "")),
                "department": dept,
                "scenario": p.get("scenario", p.get("clinical_scenario", "")),
                "urgency": p.get("urgency", "normal"),
                "lab_results": p.get("lab_results", {}),
                "present": p.get("present", p.get("history_of_present_illness", "")),
                "followup": p.get("followup", ""),
                "plan": p.get("plan", ""),
                "execution": p.get("execution", ""),
                "assessments": p.get("assessments", []),
            })

    total = len(compatible)
    page = compatible[offset:offset + limit]
    return {"total": total, "patients": page, "offset": offset, "limit": limit}


@router.get("/api/agents")
def list_agents():
    """列出所有注册的 Agent 及其工具。"""
    agents = []
    for name, p in _registry.items():
        agents.append({
            "name": p.name, "cn_name": p.cn_name, "type": p.type,
            "port": p.port, "department": p.department, "version": p.version,
            "tools": [{"name": t.name, "description": t.description} for t in p.tools],
            "depends_on": p.depends_on, "sub_agents": p.sub_agents, "parent": p.parent,
        })
    return agents


@router.get("/api/agents/{name}")
def agent_info(name: str):
    """获取单个 Agent 的详细信息。"""
    p = get_agent(name)
    if not p:
        raise HTTPException(status_code=404, detail={"error": f"Agent '{name}' not found"})
    return {
        "name": p.name, "cn_name": p.cn_name, "type": p.type,
        "port": p.port, "department": p.department, "version": p.version,
        "tools": [{"name": t.name, "description": t.description, "handler": t.handler,
                    "input": t.input} for t in p.tools],
        "guard": {"triggers": p.guard.triggers, "high_risk_scenarios": p.guard.high_risk_scenarios},
        "ui": {"template": p.ui.template, "roles": p.ui.roles, "sidebar": p.ui.sidebar},
    }


@router.get("/api/agents/{name}/knowledge")
def agent_knowledge(name: str):
    """Return knowledge base references for a specific agent."""
    agent_path = _PROJECT_ROOT / "packages" / "haip-hospital" / "agents" / "definitions" / f"{name}.yaml"
    if not agent_path.exists():
        return {"error": f"Agent {name} not found", "guidelines": [], "rules": []}

    import yaml
    data = yaml.safe_load(agent_path.read_text(encoding="utf-8"))

    # Extract knowledge references from the handler module
    guidelines: list[str] = []
    rules: list[str] = []
    kb_stats = {"guidelines_count": 0, "rules_count": 0}

    try:
        import importlib
        module_name = f"modules.{name.replace('-', '_')}"
        mod = importlib.import_module(module_name)
        agent_obj = getattr(mod, "_agent", None)
        if agent_obj and hasattr(agent_obj, "rule_engine"):
            gs = getattr(mod, "_GUIDELINES", [])
            guidelines = gs if isinstance(gs, list) else []
            try:
                all_rules = agent_obj.rule_engine.get_rules()
                rules = [r.get("name", str(r)) for r in (all_rules or [])]
            except Exception:
                logger.debug("agent rule_engine.get_rules() failed for %s", name, exc_info=True)
    except Exception:
        logger.debug("agent knowledge module load failed for %s", name, exc_info=True)

    # Also fetch from knowledge runtime
    try:
        from haip.web_server import get_kb
        kb = get_kb(str(_PROJECT_ROOT))
        kb_stats = kb.stats()
    except Exception:
        logger.debug("knowledge runtime stats failed", exc_info=True)

    return {
        "agent": name,
        "guidelines": guidelines,
        "guidelines_count": len(guidelines),
        "rules": rules,
        "rules_count": len(rules),
        "knowledge_stats": kb_stats,
    }


@router.get("/api/agent-ui/{agent_name}")
def agent_ui_config(agent_name: str):
    """快速 UI 生成器 — 根据 YAML 定义返回 UI 配置。"""
    p = get_agent(agent_name)
    if not p:
        raise HTTPException(status_code=404, detail={"error": "not found"})
    tabs = []
    for tool in p.tools:
        tabs.append({"id": tool.name, "label": tool.name, "desc": tool.description,
                     "inputs": tool.input})
    return {"agent": p.name, "cn_name": p.cn_name, "type": p.type,
            "tabs": tabs, "roles": p.ui.roles, "sidebar": p.ui.sidebar}
