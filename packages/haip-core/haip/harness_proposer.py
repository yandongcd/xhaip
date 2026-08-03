"""HarnessProposer — Mechanism-diverse multi-proposer for xhaip self-harness.

Generates targeted harness improvement proposals from diagnosis briefs,
using mechanism families adapted for xhaip's YAML-agent domain:
  - prompt_instruction: Edit system prompts
  - guard_rule: Add/modify guard triggers
  - tool_configuration: Add/modify tool definitions
  - stage_workflow: Add/modify clinical stage definitions
  - citation_policy: Enforce citation requirements

Mirrors the proposer module from qzzqzzb/Self-Harness, adapted for xhaip agents.

Usage:
    proposer = HarnessProposer(llm=provider)
    bundle = proposer.generate(diagnosis_brief, surfaces)
"""

from __future__ import annotations

import json
import logging
import pathlib
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import yaml

from haip.llm import LLMProvider

logger = logging.getLogger(__name__)

_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


# ══════════════════════════════════════════════════════════════════
# MECHANISM FAMILIES & HOOKS (adapted for xhaip YAML agents)
# ══════════════════════════════════════════════════════════════════

MECHANISM_FAMILIES = {
    "prompt_instruction": "system_prompt",
    "guard_rule": "guard_triggers",
    "tool_configuration": "tool_definitions",
    "stage_workflow": "stage_definitions",
    "citation_policy": "citation_enforcement",
}

HOOKS_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "prompt_instruction": ("system_prompt",),
    "guard_rule": ("triggers", "high_risk_scenarios"),
    "tool_configuration": ("tools", "handler"),
    "stage_workflow": ("stages", "role_ids"),
    "citation_policy": ("citation", "required"),
}


@dataclass(frozen=True)
class EditableSurface:
    name: str
    kind: str
    target: str
    current_value: str
    filename: str | None = None

    def to_prompt_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "target": self.target,
            "filename": self.filename,
            "current_value": self.current_value[:2000],
        }


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    title: str
    selected_cluster: str
    selected_surface: str
    mechanism: str
    mechanism_family: str
    exact_hook: str
    why_distinct: str
    net_gain_hypothesis: str
    regression_guard: str
    summary: str
    final_message: str | None
    candidate_values: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ProposalBundle:
    proposals: tuple[Proposal, ...]
    diagnosis_ref: str
    created_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "proposals": [p.to_dict() for p in self.proposals],
            "diagnosis_ref": self.diagnosis_ref,
            "created_at": self.created_at,
        }


class HarnessProposer:
    """Multi-proposer generating diverse harness improvement candidates."""

    def __init__(
        self,
        project_root: str = "",
        llm: LLMProvider | None = None,
        route_count: int = 4,
    ):
        if project_root:
            self.root = pathlib.Path(project_root)
        else:
            self.root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        self.agents_dir = self.root / "packages/haip-hospital/agents/definitions"
        self.llm = llm
        self.route_count = route_count

    def generate(
        self,
        diagnosis_brief: str,
        surfaces: list[EditableSurface] | None = None,
    ) -> ProposalBundle:
        """Generate mechanism-diverse proposals from a diagnosis brief."""
        if surfaces is None:
            surfaces = self._auto_discover_surfaces()

        proposals: list[Proposal] = []
        used_mechanisms: set[str] = set()

        for slot in range(self.route_count):
            proposal = self._generate_slot(diagnosis_brief, surfaces, slot, proposals)
            if proposal:
                proposals.append(proposal)
                used_mechanisms.add(proposal.mechanism_family)

        return ProposalBundle(
            proposals=tuple(proposals),
            diagnosis_ref=diagnosis_brief[:200],
            created_at=time.time(),
        )

    def _generate_slot(
        self,
        diagnosis_brief: str,
        surfaces: list[EditableSurface],
        slot: int,
        existing: list[Proposal],
    ) -> Proposal | None:
        """Generate a single proposal slot, ensuring mechanism diversity."""
        used_families = {p.mechanism_family for p in existing}
        available = [f for f in MECHANISM_FAMILIES if f not in used_families]

        if not available:
            return None

        family = available[slot % len(available)]

        if self.llm is None:
            return self._rule_based_proposal(diagnosis_brief, surfaces, slot, family)

        return self._llm_proposal(diagnosis_brief, surfaces, slot, family, existing)

    def _rule_based_proposal(
        self,
        diagnosis_brief: str,
        surfaces: list[EditableSurface],
        slot: int,
        family: str,
    ) -> Proposal:
        """Generate proposals using rule-based heuristics when no LLM available."""
        proposals_by_family = {
            "prompt_instruction": Proposal(
                proposal_id=f"improve-{family}-{slot}",
                title=f"Improve {family} for affected agents",
                selected_cluster="failure_patterns",
                selected_surface="system_prompt",
                mechanism="Add clinical context to system prompts",
                mechanism_family=family,
                exact_hook="system_prompt",
                why_distinct="Prompt refinement targets instruction quality directly",
                net_gain_hypothesis="Better prompts reduce tool misuse and improve guard compliance",
                regression_guard="Preserve existing role definitions and clinical constraints",
                summary="Enhance system prompts with domain-specific clinical guidance",
                final_message="Updated system prompts with clinical context",
                candidate_values={"system_prompt": "enhanced"},
            ),
            "guard_rule": Proposal(
                proposal_id=f"add-{family}-{slot}",
                title="Add guard triggers for failing agents",
                selected_cluster="guard_missing",
                selected_surface="guard_triggers",
                mechanism="Add missing guard triggers and high_risk_scenarios",
                mechanism_family=family,
                exact_hook="triggers",
                why_distinct="Guard rules prevent unsafe operations",
                net_gain_hypothesis="Guard triggers catch unsafe operations before execution",
                regression_guard="Don't remove existing citation or trigger rules",
                summary="Add guard triggers and high_risk_scenarios to agents missing them",
                final_message="Added guard triggers to affected agents",
                candidate_values={"triggers": ["诊断决策", "治疗方案"]},
            ),
            "tool_configuration": Proposal(
                proposal_id=f"fix-{family}-{slot}",
                title="Fix broken tool handlers",
                selected_cluster="handler_error",
                selected_surface="tool_definitions",
                mechanism="Validate and fix tool handler paths",
                mechanism_family=family,
                exact_hook="handler",
                why_distinct="Broken handlers cause immediate failures",
                net_gain_hypothesis="Fixed handlers eliminate import-time failures",
                regression_guard="Preserve existing handler signatures",
                summary="Fix broken tool handler module paths and function references",
                final_message="Fixed tool handler paths",
                candidate_values={"handler": "validated"},
            ),
            "stage_workflow": Proposal(
                proposal_id=f"complete-{family}-{slot}",
                title="Complete clinical stage definitions",
                selected_cluster="stage_incomplete",
                selected_surface="stage_definitions",
                mechanism="Add missing role_ids and stage descriptions",
                mechanism_family=family,
                exact_hook="role_ids",
                why_distinct="Incomplete stages break role-based UI",
                net_gain_hypothesis="Complete stage definitions enable proper role assignment",
                regression_guard="Preserve existing stage ordering and boundaries",
                summary="Add role_ids and descriptions to stages missing them",
                final_message="Completed stage definitions",
                candidate_values={"role_ids": ["physician", "nurse"]},
            ),
            "citation_policy": Proposal(
                proposal_id=f"enforce-{family}-{slot}",
                title="Enforce citation requirements for high-risk agents",
                selected_cluster="citation_missing",
                selected_surface="citation_enforcement",
                mechanism="Add citation enforcement to high-risk scenarios",
                mechanism_family=family,
                exact_hook="required",
                why_distinct="Citation enforcement is critical for clinical safety",
                net_gain_hypothesis="Citation enforcement ensures evidence-based decisions",
                regression_guard="Don't add citations to non-clinical agents",
                summary="Enable citation enforcement for agents with high_risk_scenarios",
                final_message="Enabled citation enforcement",
                candidate_values={"required": True},
            ),
        }
        return proposals_by_family.get(family, proposals_by_family["guard_rule"])

    def _llm_proposal(
        self,
        diagnosis_brief: str,
        surfaces: list[EditableSurface],
        slot: int,
        family: str,
        existing: list[Proposal],
    ) -> Proposal | None:
        if self.llm is None:
            return self._rule_based_proposal(diagnosis_brief, surfaces, slot, family)

        hooks = HOOKS_BY_FAMILY.get(family, ("unknown",))
        existing_payload = [
            {"proposal_id": p.proposal_id, "mechanism_family": p.mechanism_family}
            for p in existing
        ]

        prompt = (
            f"You are a mechanism-diverse multi-proposer for xhaip self-harness.\n"
            f"Generate exactly ONE candidate proposal for mechanism family '{family}'.\n"
            f"Available hooks: {', '.join(hooks)}\n\n"
            f"Return compact JSON only with this shape:\n"
            f'{{"proposal_id":"slug","title":"title","selected_cluster":"cluster","selected_surface":"surface",'
            f'"mechanism":"description","mechanism_family":"{family}","exact_hook":"hook_name",'
            f'"why_distinct":"why unique","net_gain_hypothesis":"how improves","regression_guard":"what preserves",'
            f'"summary":"markdown summary","final_message":"brief note",'
            f'"candidate_values":{{"hook":"value"}}}}\n\n'
            f"# Already Generated\n{json.dumps(existing_payload, indent=2)}\n\n"
            f"# Editable Surfaces\n{json.dumps([s.to_prompt_dict() for s in surfaces], indent=2)}\n\n"
            f"# Diagnosis Brief\n{diagnosis_brief[:4000]}"
        )

        try:
            resp = self.llm.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "Generate diverse, evidence-backed harness improvement proposals. Return ONLY strict JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=3000,
            )
            return self._parse_proposal(resp.content, family, slot)
        except Exception:
            return self._rule_based_proposal(diagnosis_brief, surfaces, slot, family)

    def _parse_proposal(self, text: str, family: str, slot: int) -> Proposal | None:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            match = _JSON_OBJECT_RE.search(text)
            if not match:
                return None
            payload = json.loads(match.group(0))

        if not isinstance(payload, dict):
            return None

        return Proposal(
            proposal_id=str(payload.get("proposal_id", f"{family}-{slot}")),
            title=str(payload.get("title", f"{family} improvement #{slot}")),
            selected_cluster=str(payload.get("selected_cluster", "unknown")),
            selected_surface=str(payload.get("selected_surface", family)),
            mechanism=str(payload.get("mechanism", f"Improve {family}")),
            mechanism_family=family,
            exact_hook=str(payload.get("exact_hook", "")),
            why_distinct=str(payload.get("why_distinct", "N/A")),
            net_gain_hypothesis=str(payload.get("net_gain_hypothesis", "N/A")),
            regression_guard=str(payload.get("regression_guard", "N/A")),
            summary=str(payload.get("summary", "N/A")),
            final_message=payload.get("final_message"),
            candidate_values=payload.get("candidate_values", {}),
            metadata={"slot": slot, "parser": "llm"},
        )

    def _auto_discover_surfaces(self) -> list[EditableSurface]:
        surfaces: list[EditableSurface] = []
        if self.agents_dir.exists():
            for yf in sorted(self.agents_dir.glob("*.yaml")):
                try:
                    content = yf.read_text(encoding="utf-8")
                    data = yaml.safe_load(content)
                    name = data.get("name", yf.stem)
                    surfaces.append(
                        EditableSurface(
                            name=name,
                            kind="agent_yaml",
                            target=str(yf),
                            current_value=content,
                            filename=yf.name,
                        )
                    )
                except Exception:
                    logger.debug("Proposal surface parse failed: %s", yf, exc_info=True)
        return surfaces

    def materialize(
        self, proposal: Proposal, output_dir: pathlib.Path | None = None
    ) -> dict[str, Any]:
        """Materialize a proposal into a candidate manifest."""
        if output_dir is None:
            output_dir = self.root / ".openharness" / "runtime" / "candidates" / proposal.proposal_id
        output_dir = pathlib.Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "candidate_id": proposal.proposal_id,
            "proposal_id": proposal.proposal_id,
            "changed_surfaces": [proposal.selected_surface],
            "mechanism_family": proposal.mechanism_family,
            "exact_hook": proposal.exact_hook,
            "candidate_values": proposal.candidate_values,
            "metadata": proposal.metadata,
        }

        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        proposal_path = output_dir / "proposal.json"
        proposal_path.write_text(json.dumps(proposal.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        md_path = output_dir / "proposal.md"
        md_path.write_text(proposal.summary.rstrip() + "\n", encoding="utf-8")

        return manifest


def apply_candidate(proposal: Proposal, project_root: pathlib.Path) -> dict[str, Any]:
    """Apply a candidate proposal to the actual agent YAML files."""
    agents_dir = project_root / "packages/haip-hospital/agents/definitions"
    results: dict[str, Any] = {"proposal_id": proposal.proposal_id, "changes": [], "errors": []}

    family = proposal.mechanism_family
    values = proposal.candidate_values

    for yf in sorted(agents_dir.glob("*.yaml")):
        try:
            content = yf.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            changed = False

            if family == "guard_rule":
                if "guard" not in data:
                    data["guard"] = {}
                for hook_key in ("triggers", "high_risk_scenarios"):
                    if hook_key in data["guard"] and data["guard"][hook_key]:
                        continue
                    new_val = values.get(hook_key)
                    if isinstance(new_val, list) and new_val:
                        data["guard"][hook_key] = new_val
                        changed = True

            elif family == "citation_policy":
                if "guard" not in data:
                    data["guard"] = {}
                if "citation" not in data["guard"]:
                    data["guard"]["citation"] = {}
                if not data["guard"].get("citation", {}).get("required"):
                    data["guard"]["citation"]["required"] = values.get("required", True)
                    changed = True

            if changed:
                yf.write_text(
                    yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False, width=200),
                    encoding="utf-8",
                )
                results["changes"].append(str(yf.name))

        except Exception as e:
            results["errors"].append(f"{yf.name}: {e}")

    return results
