"""多提案生成+提案应用 — meta_harness mixin (P1-6 拆分)."""

from __future__ import annotations

import json
import logging
import os
import pathlib
import sqlite3
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import yaml

from haip.harness_proposer import HarnessProposer, Proposal, apply_candidate

logger = logging.getLogger(__name__)


class MetaHarnessProposerMixin:
    def _run_multi_proposer(self, diagnosis_stage: dict) -> dict:
        """Generate mechanism-diverse improvement proposals from diagnosis."""
        diagnosis_brief = self._load_diagnosis_brief()
        if not diagnosis_brief:
            diagnosis_clusters = diagnosis_stage.get("clusters", [])
            if diagnosis_clusters:
                lines = ["# Auto-Generated Diagnosis", ""]
                lines.append(f"Found {len(diagnosis_clusters)} failure clusters.")
                for c in diagnosis_clusters[:5]:
                    sig = c.get("signature", ("?", "?", "?"))
                    lines.append(f"- {sig[0]} / {sig[1]} / {sig[2]} ({c.get('cases', 0)} cases)")
                diagnosis_brief = "\n".join(lines)

        bundle = self._proposer.generate(diagnosis_brief)

        # Save bundle
        bundle_path = self.root / ".openharness" / "runtime" / "proposal_bundle.json"
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text(json.dumps(bundle.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        return {
            "status": "completed",
            "total_proposals": len(bundle.proposals),
            "proposals": [
                {
                    "id": p.proposal_id,
                    "title": p.title,
                    "mechanism_family": p.mechanism_family,
                    "exact_hook": p.exact_hook,
                    "summary": p.summary[:200],
                }
                for p in bundle.proposals
            ],
            "bundle_path": str(bundle_path),
            "score": min(100, len(bundle.proposals) * 25),
        }


    def _load_diagnosis_brief(self) -> str:
        brief_path = self.root / ".openharness" / "runtime" / "diagnosis_brief.md"
        if brief_path.exists():
            return brief_path.read_text(encoding="utf-8")
        return ""

    # ═══ STAGE 8: Acceptance Gate (Self-Harness-style) ═══


    def apply_proposal(self, proposal_id: str) -> dict[str, Any]:
        """Apply a specific proposal from the stored bundle."""
        bundle_path = self.root / ".openharness" / "runtime" / "proposal_bundle.json"
        if not bundle_path.exists():
            return {"error": "No proposal bundle found. Run multi_proposer stage first."}

        bundle_data = json.loads(bundle_path.read_text(encoding="utf-8"))
        proposals = bundle_data.get("proposals", [])

        matched = [p for p in proposals if p.get("proposal_id") == proposal_id]
        if not matched:
            return {"error": f"No proposal found with id '{proposal_id}'"}

        raw = matched[0]
        extra_fields = set(raw.keys()) - {
            "proposal_id", "title", "selected_cluster", "selected_surface",
            "mechanism", "mechanism_family", "exact_hook", "why_distinct",
            "net_gain_hypothesis", "regression_guard", "summary", "final_message",
            "candidate_values", "metadata",
        }
        metadata = {k: raw[k] for k in extra_fields if k in raw}
        proposal = Proposal(
            proposal_id=raw.get("proposal_id", ""),
            title=raw.get("title", ""),
            selected_cluster=raw.get("selected_cluster", ""),
            selected_surface=raw.get("selected_surface", ""),
            mechanism=raw.get("mechanism", ""),
            mechanism_family=raw.get("mechanism_family", ""),
            exact_hook=raw.get("exact_hook", ""),
            why_distinct=raw.get("why_distinct", ""),
            net_gain_hypothesis=raw.get("net_gain_hypothesis", ""),
            regression_guard=raw.get("regression_guard", ""),
            summary=raw.get("summary", ""),
            final_message=raw.get("final_message"),
            candidate_values=raw.get("candidate_values", {}),
            metadata=metadata,
        )

        change_result = apply_candidate(proposal, self.root)
        materialize_result = self._proposer.materialize(proposal)

        return {
            "status": "applied",
            "proposal_id": proposal_id,
            "changes": change_result,
            "manifest": materialize_result,
        }


    def run_proposer_loop(self, max_iterations: int = 3) -> dict[str, Any]:
        """Full self-harness loop: diagnose → propose → apply → evaluate."""
        results = []

        for i in range(max_iterations):
            diag = self._run_causal_diagnosis()
            if diag.get("clusters_count", 0) == 0:
                break

            prop = self._run_multi_proposer(diag)
            if prop.get("total_proposals", 0) == 0:
                break

            for p in prop.get("proposals", []):
                apply_result = self.apply_proposal(p["id"])
                results.append(apply_result)

            gate = self._run_acceptance_gate({
                "auto_testing": self._run_auto_testing(),
                "rlaif_audit": self._run_rlaif_audit(),
            })

            if gate["accepted"]:
                self._snapshot.record(
                    "harness_loop",
                    {"accepted": True, "iteration": i + 1},
                    {"gate": gate},
                )
            else:
                break

        return {
            "iterations": max_iterations,
            "results_count": len(results),
            "results": results,
        }


# ═══ API ═══

_singleton_state: dict = {}


