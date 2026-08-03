"""HarnessDiagnosis — Trace-based causal diagnosis for xhaip self-harness.

Normalizes agent execution traces, uses LLM to identify terminal failure causes,
clusters failures by causal signatures, and generates diagnosis briefs for the proposer.

Mirrors the diagnosis module from qzzqzzb/Self-Harness (arXiv:2606.09498),
adapted for xhaip's YAML-agent domain.

Usage:
    diagnosis = HarnessDiagnosis(llm=provider)
    brief = diagnosis.run(failed_executions)  # Markdown diagnosis brief
"""

from __future__ import annotations

import json
import logging
import pathlib
import re
import sqlite3
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from haip.llm import LLMProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiagnosisConfig:
    model_reference: str | None = None
    timeout_s: float | None = 180.0
    retries: int = 1

    def to_dict(self) -> dict:
        return {
            "model_reference": self.model_reference,
            "timeout_s": self.timeout_s,
            "retries": self.retries,
        }


@dataclass
class NormalizedStep:
    step_id: int
    kind: str
    assistant_summary: str
    tool_calls: list[dict]
    tool_results: list[dict]

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "kind": self.kind,
            "assistant_summary": self.assistant_summary[:500],
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
        }


@dataclass
class StageRecord:
    stage_id: int
    step_ids: list[int]
    boundary_step_id: int
    boundary_type: str

    def to_dict(self) -> dict:
        return {
            "stage_id": self.stage_id,
            "step_ids": self.step_ids,
            "boundary_step_id": self.boundary_step_id,
            "boundary_type": self.boundary_type,
        }


@dataclass(frozen=True)
class DiagnosisOutcome:
    case_id: str
    split: str
    stratum: str
    status: str
    failure_message: str | None = None
    artifacts_dir: str | None = None
    messages_path: str | None = None

    @property
    def passed(self) -> bool:
        return self.status in ("passed", "ok")


DiagnosisLoader = Callable[["DiagnosisOutcome"], dict[str, Any] | None]
VerifierCausalSignature = tuple[str, str, str]

_CHANGE_TOOL_RE = re.compile(
    r"(write|edit|patch|replace|update|create|delete|remove|append|insert|"
    r"submit|save|commit)",
    re.IGNORECASE,
)
_SIGNATURE_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]{1,119}$")
_CRITICALITY_VALUES = {
    "root_cause",
    "contributor",
    "non_terminal_friction",
    "recovered_friction",
    "unknown",
}


class HarnessDiagnosis:
    """Trace-based causal diagnosis for xhaip agents."""

    def __init__(
        self,
        project_root: str = "",
        llm: LLMProvider | None = None,
        config: DiagnosisConfig | None = None,
    ):
        if project_root:
            self.root = pathlib.Path(project_root)
        else:
            self.root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        self.db_path = self.root / "xhaip_memory.db"
        self.llm = llm
        self.config = config or DiagnosisConfig()

    def run(self, executions: list[dict] | None = None) -> dict[str, Any]:
        """Run full diagnosis cycle: normalize traces, cluster failures, generate brief."""
        if executions is None:
            executions = self._load_failed_executions()

        outcomes = self._build_outcomes(executions)
        clusters = self._build_causal_clusters(outcomes)
        brief = self._write_causal_brief(outcomes, clusters)

        return {
            "format": "self_harness.diagnosis.v1",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_executions": len(executions),
            "failed_cases": len([o for o in outcomes if not o.passed]),
            "passing_cases": len([o for o in outcomes if o.passed]),
            "clusters_count": len(clusters),
            "clusters": clusters,
            "diagnosis_brief": brief,
        }

    def _load_failed_executions(self) -> list[dict]:
        if not self.db_path.exists():
            return []
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT agent, tool, status, patient_id, input_params, result, timestamp "
                    "FROM decisions WHERE status != 'ok' ORDER BY timestamp DESC LIMIT 200"
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            logger.debug("Execution history DB read failed", exc_info=True)
            return []

    def _build_outcomes(self, executions: list[dict]) -> list[DiagnosisOutcome]:
        outcomes = []
        for i, ex in enumerate(executions):
            status = ex.get("status", "ok")
            failure = None
            if status != "ok":
                failure = f"Agent '{ex.get('agent','')}' tool '{ex.get('tool','')}' failed"
                result = ex.get("result", "")
                if isinstance(result, str):
                    try:
                        result_data = json.loads(result)
                        if isinstance(result_data, dict):
                            msg = result_data.get("error") or result_data.get("message", "")
                            if msg:
                                failure += f": {msg[:200]}"
                    except json.JSONDecodeError:
                        failure += f": {result[:200]}"
            outcomes.append(
                DiagnosisOutcome(
                    case_id=f"{ex.get('agent','unknown')}:{ex.get('tool','unknown')}#{i}",
                    split="train",
                    stratum=ex.get("tool", "unknown"),
                    status=status,
                    failure_message=failure,
                )
            )
        return outcomes

    def _build_causal_clusters(self, outcomes: list[DiagnosisOutcome]) -> list[dict]:
        failing = [o for o in outcomes if not o.passed]

        records: list[dict] = []
        for outcome in failing:
            diagnosis = self._diagnose_outcome(outcome)
            if diagnosis:
                records.append({
                    "outcome": outcome,
                    "diagnosis": diagnosis,
                    "signature": self._causal_signature(outcome, diagnosis),
                })

        grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
        for record in records:
            grouped[record["signature"]].append(record)

        clusters = [
            {
                "signature": sig,
                "cases": len(recs),
                "strata": sorted({r["outcome"].stratum for r in recs}),
                "representative": recs[0]["outcome"].case_id,
            }
            for sig, recs in sorted(grouped.items(), key=lambda x: -len(x[1]))
        ]
        return clusters

    def _diagnose_outcome(self, outcome: DiagnosisOutcome) -> dict[str, Any] | None:
        if self.llm is None:
            return self._simple_diagnosis(outcome)
        return self._llm_diagnosis(outcome)

    def _simple_diagnosis(self, outcome: DiagnosisOutcome) -> dict[str, Any]:
        failure_kind = "handler_error"
        msg = outcome.failure_message or ""
        msg_lower = msg.lower()

        if "import" in msg_lower or "module" in msg_lower:
            failure_kind = "missing_handler"
        elif "timeout" in msg_lower:
            failure_kind = "agent_timeout"
        elif "guard" in msg_lower:
            failure_kind = "guard_missing"
        elif "citation" in msg_lower:
            failure_kind = "citation_missing"
        elif "role" in msg_lower:
            failure_kind = "role_missing"
        elif "stage" in msg_lower:
            failure_kind = "stage_incomplete"

        return {
            "analysis": [
                {
                    "stage_id": 1,
                    "incorrect_step_ids": [1],
                    "unuseful_step_ids": [],
                    "reasoning": msg,
                    "terminal_cause": failure_kind,
                    "criticality": "root_cause",
                    "agent_mechanism": failure_kind,
                    "terminal_link": "direct",
                    "causal_weight": "root_cause",
                    "selected_step_recovered": False,
                    "missed_oracle": "",
                }
            ],
            "verifier_evidence": {
                "terminal_summary": msg,
                "reward_text": "",
                "failure_snippets": [msg],
            },
            "causal_summary": f"{failure_kind}: {msg}",
        }

    def _llm_diagnosis(self, outcome: DiagnosisOutcome) -> dict[str, Any] | None:
        prompt = self._build_diagnosis_prompt(outcome)
        for _ in range(max(1, self.config.retries)):
            try:
                resp = self.llm.chat(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Analyze a failed xhaip agent execution. Return only strict JSON with key 'analysis'. "
                                "Each item must contain: terminal_cause (snake_case), criticality "
                                "(root_cause|contributor|non_terminal_friction|recovered_friction|unknown), "
                                "agent_mechanism (snake_case reusable pattern), reasoning (evidence chain), "
                                "and terminal_link (direct|indirect|weak|none|unknown)."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                )
                analysis = self._parse_llm_analysis(resp.content)
                if analysis:
                    return {"analysis": analysis, "causal_summary": self._causal_summary_from_analysis(analysis, outcome)}
            except Exception:
                logger.debug("LLM causal diagnosis failed for %s", outcome.case_id, exc_info=True)
        return self._simple_diagnosis(outcome)

    def _build_diagnosis_prompt(self, outcome: DiagnosisOutcome) -> str:
        return (
            f"Task: xhaip Agent '{outcome.case_id}'\n"
            f"Failure message: {outcome.failure_message or 'unknown'}\n"
            f"Status: {outcome.status}\n\n"
            "Instructions:\n"
            "- Identify the root cause terminal signature from the failure evidence.\n"
            "- terminal_cause must be a concise snake_case causal terminal signature.\n"
            "- agent_mechanism must be a reusable behavior pattern observed in the run.\n"
            "- Return only JSON."
        )

    def _parse_llm_analysis(self, text: str) -> list[dict]:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                return []
            payload = json.loads(match.group(0))
        items = payload.get("analysis") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            return []
        return items if all(isinstance(item, dict) for item in items) else []

    def _causal_summary_from_analysis(self, analysis: list[dict], outcome: DiagnosisOutcome) -> str:
        if not analysis:
            return str(outcome.failure_message or "")
        first = analysis[0]
        cause = first.get("terminal_cause", "unknown")
        reasoning = first.get("reasoning", "")
        return f"{cause}: {reasoning[:200]}"

    def _causal_signature(self, outcome: DiagnosisOutcome, diagnosis: dict) -> VerifierCausalSignature:
        analysis = diagnosis.get("analysis", [])
        if not analysis:
            return ("unknown", "unknown", "unknown")
        item = analysis[0]
        return (
            str(item.get("terminal_cause", "unknown")),
            str(item.get("criticality", "unknown")),
            str(item.get("agent_mechanism", "unknown")),
        )

    def _write_causal_brief(self, outcomes: list[DiagnosisOutcome], clusters: list[dict]) -> str:
        passing = [o.case_id for o in outcomes if o.passed]
        failing = [o.case_id for o in outcomes if not o.passed]

        lines = [
            "# Self-Harness Diagnosis Brief",
            "",
            "Use this diagnosis to generate harness improvement proposals.",
            "",
            "## Passing Cases To Preserve",
            "",
        ]
        lines.extend([f"- `{c}`" for c in passing[:20]] or ["- None"])
        lines.append("")
        lines.append(f"Total passing: {len(passing)}, failing: {len(failing)}")

        if failing:
            lines.extend([
                "",
                "## Failure Clusters",
                "",
            ])
            for i, cluster in enumerate(clusters[:10]):
                sig = cluster["signature"]
                lines.append(
                    f"### Cluster {i + 1}: {sig[0]} / {sig[1]} / {sig[2]}"
                )
                lines.append(f"- Cases: {cluster['cases']}")
                lines.append(f"- Strata: {', '.join(cluster['strata'])}")
                lines.append(f"- Representative: `{cluster['representative']}`")
                lines.append("")

        return "\n".join(lines)


def normalize_trace_steps(messages: list[dict]) -> list[NormalizedStep]:
    steps: list[NormalizedStep] = []
    cursor = 0
    index = 0
    while cursor < len(messages):
        msg = messages[cursor]
        msg_type = str(msg.get("type", "") or msg.get("role", "")).lower()
        if msg_type not in ("ai", "assistant"):
            cursor += 1
            continue

        tool_calls = _extract_tool_calls(msg)
        tool_results = []
        lookahead = cursor + 1
        while lookahead < len(messages) and str(messages[lookahead].get("type", "")).lower() == "tool":
            tool_results.append(_extract_tool_result(messages[lookahead]))
            lookahead += 1

        index += 1
        steps.append(
            NormalizedStep(
                step_id=index,
                kind="change" if any(_CHANGE_TOOL_RE.search(c["name"]) for c in tool_calls) else "explore",
                assistant_summary=_message_text(msg)[:500],
                tool_calls=tool_calls,
                tool_results=tool_results,
            )
        )
        cursor = lookahead
    return steps


def build_stage_records(steps: list[NormalizedStep]) -> list[StageRecord]:
    records: list[StageRecord] = []
    stage_steps: list[int] = []
    stage_id = 1
    for step in steps:
        stage_steps.append(step.step_id)
        if step.kind == "change":
            records.append(
                StageRecord(
                    stage_id=stage_id,
                    step_ids=stage_steps,
                    boundary_step_id=step.step_id,
                    boundary_type=step.kind,
                )
            )
            stage_id += 1
            stage_steps = []
    if stage_steps:
        records.append(
            StageRecord(
                stage_id=stage_id,
                step_ids=stage_steps,
                boundary_step_id=stage_steps[-1],
                boundary_type="explore",
            )
        )
    return records


def _extract_tool_calls(msg: dict) -> list[dict]:
    raw = msg.get("tool_calls", [])
    if not isinstance(raw, list):
        return []
    return [
        {"name": c.get("name", ""), "args": c.get("args", {}) if isinstance(c.get("args"), dict) else {}}
        for c in raw
        if isinstance(c, dict)
    ]


def _extract_tool_result(msg: dict) -> dict:
    content = str(msg.get("content", "") or "")
    return {
        "name": str(msg.get("name", "") or ""),
        "status": str(msg.get("status")) if msg.get("status") is not None else None,
        "content_excerpt": content[:500],
    }


def _message_text(msg: dict) -> str:
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content or "")
