"""Intelligent Clinical Workflow Planner — 智能规划.

Dynamically generates multi-step clinical plans by composing base agents,
clinical rules, and patient-specific data. Supports agent reuse and adaptive planning.

Usage:
    planner = WorkflowPlanner()
    plan = planner.plan("cardiology", patient_data)
    # -> {"steps": [...], "agents_used": [...], "estimated_duration": "..."}
"""

from __future__ import annotations

import pathlib
import yaml
from collections import defaultdict
from typing import Any


class WorkflowPlanner:
    """Dynamically plans clinical workflows using agent composition."""

    def __init__(self, project_root: str = ""):
        if project_root:
            self.root = pathlib.Path(project_root)
        else:
            self.root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        self.agents_dir = self.root / "packages/haip-hospital/agents/definitions"
        self._agent_registry: dict[str, dict] = {}

    def plan(self, agent_name: str, patient: dict[str, Any]) -> dict[str, Any]:
        """Generate a dynamic care plan for a patient.

        Returns:
            {
                "steps": [{"order": 1, "agent": "cardiology", "action": "诊断评估", "reasoning": "..."}],
                "agents_used": ["cardiology", "pharmacy"],
                "estimated_duration": "3-5天",
                "adaptive": True
            }
        """
        self._load_agents()
        primary = self._agent_registry.get(agent_name, {})
        steps = []

        # Step 1: Always start with primary agent assessment
        steps.append({
            "order": 1,
            "agent": agent_name,
            "action": "初步评估",
            "reasoning": f"由{primary.get('cn_name', agent_name)}进行初步评估",
        })

        # Step 2: Identify dependencies and compose agents
        depends_on = primary.get("depends_on", [])
        for i, dep in enumerate(depends_on, start=2):
            dep_agent = dep.get("agent", "")
            if dep_agent in self._agent_registry:
                steps.append({
                    "order": i,
                    "agent": dep_agent,
                    "action": f"协同评估",
                    "reasoning": f"依赖{self._agent_registry[dep_agent].get('cn_name', dep_agent)}的数据支持",
                })

        # Step 3: Check for related specialists based on diagnosis
        diagnosis = patient.get("diagnosis", "")
        related = self._find_related_agents(diagnosis, agent_name)
        for i, ra in enumerate(related, start=len(steps) + 1):
            steps.append({
                "order": i,
                "agent": ra,
                "action": "专科会诊",
                "reasoning": f"基于诊断'{diagnosis}'推荐{self._agent_registry.get(ra,{}).get('cn_name',ra)}会诊",
            })

        # Step 4: Pharmacy review for any medication-related cases
        if any(kw in diagnosis for kw in ["骨折", "手术", "感染", "癌", "糖尿病", "高血压"]):
            steps.append({
                "order": len(steps) + 1,
                "agent": "pharmacy",
                "action": "用药审核",
                "reasoning": "处方审核和药物相互作用检查",
            })

        # Step 5: Follow-up plan
        steps.append({
            "order": len(steps) + 1,
            "agent": agent_name,
            "action": "随访计划",
            "reasoning": "制定个性化随访方案",
        })

        agents_used = list(dict.fromkeys(s["agent"] for s in steps))

        return {
            "steps": steps,
            "agents_used": agents_used,
            "agent_count": len(agents_used),
            "step_count": len(steps),
            "adaptive": True,
            "primary_agent": agent_name,
        }

    def _load_agents(self):
        if self._agent_registry:
            return
        for yf in sorted(self.agents_dir.glob("*.yaml")):
            with open(yf, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self._agent_registry[data["name"]] = data

    def _find_related_agents(self, diagnosis: str, exclude: str) -> list[str]:
        related = []
        keyword_map = {
            "骨折": ["orthopedic-surgery", "pain-management"],
            "心": ["cardiology", "cardio-risk"],
            "脑": ["neurosurgery", "neurology"],
            "癌": ["oncology", "cancer-pain"],
            "肺": ["respiratory"],
            "肾": ["nephrology", "renal-transplant"],
            "糖尿病": ["endocrinology", "ophthalmology"],
            "感染": ["infectious-disease"],
            "妊": ["obgyn"],
            "新生儿": ["neonatology", "pediatrics"],
            "卒": ["neurosurgery", "rehabilitation"],
        }
        for kw, agents in keyword_map.items():
            if kw in diagnosis:
                for a in agents:
                    if a != exclude and a in self._agent_registry:
                        related.append(a)
        return related[:3]


_planner: WorkflowPlanner | None = None


def get_workflow_planner() -> WorkflowPlanner:
    global _planner
    if _planner is None:
        _planner = WorkflowPlanner()
    return _planner
