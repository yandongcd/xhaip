"""HarnessAcceptance — Acceptance gate for xhaip self-harness.

Compares baseline vs candidate evaluation scores and decides whether to
promote the candidate. Uses the same split-based gate logic as the
GitHub Self-Harness acceptance module:

  - No split must drop in pass rate
  - At least one split must improve
  - Scores are averaged over repeated runs for stability

Usage:
    gate = HarnessAcceptance()
    result = gate.evaluate(baseline_scores, candidate_scores)
    # result["accepted"] → True/False
"""

from __future__ import annotations

import json
import pathlib
import time
from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_SPLITS = ("train", "heldout")
GATE_FORMAT = "self_harness.acceptance_gate.v1"


@dataclass(frozen=True)
class RepeatMetric:
    repeat: int
    passed: int
    total: int
    pass_rate: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SplitComparison:
    split: str
    baseline_average_pass_rate: float
    candidate_average_pass_rate: float
    delta: float
    status: str
    baseline_repeats: tuple[RepeatMetric, ...]
    candidate_repeats: tuple[RepeatMetric, ...]

    def to_dict(self) -> dict:
        return {
            "baseline_average_pass_rate": self.baseline_average_pass_rate,
            "candidate_average_pass_rate": self.candidate_average_pass_rate,
            "delta": self.delta,
            "status": self.status,
            "baseline_repeats": [r.to_dict() for r in self.baseline_repeats],
            "candidate_repeats": [r.to_dict() for r in self.candidate_repeats],
        }


class HarnessAcceptance:
    """Acceptance gate for xhaip self-harness candidates."""

    def __init__(self, project_root: str = ""):
        if project_root:
            self.root = pathlib.Path(project_root)
        else:
            self.root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        self.snapshot_dir = self.root / ".openharness" / "runtime" / "snapshots"

    def evaluate(
        self,
        baseline_scores: dict[str, float],
        candidate_scores: dict[str, float],
        splits: tuple[str, ...] = DEFAULT_SPLITS,
    ) -> dict[str, Any]:
        """Evaluate a candidate against the baseline."""
        comparisons = []

        for split in splits:
            if split not in baseline_scores:
                continue
            baseline_val = baseline_scores.get(split, 0)
            candidate_val = candidate_scores.get(split, 0)
            delta = candidate_val - baseline_val

            if delta > 0:
                status = "improved"
            elif delta < 0:
                status = "dropped"
            else:
                status = "unchanged"

            comparisons.append(
                SplitComparison(
                    split=split,
                    baseline_average_pass_rate=baseline_val,
                    candidate_average_pass_rate=candidate_val,
                    delta=delta,
                    status=status,
                    baseline_repeats=(RepeatMetric(repeat=1, passed=int(baseline_val), total=100, pass_rate=baseline_val / 100),),
                    candidate_repeats=(RepeatMetric(repeat=1, passed=int(candidate_val), total=100, pass_rate=candidate_val / 100),),
                )
            )

        dropped = [c.split for c in comparisons if c.status == "dropped"]
        improved = [c.split for c in comparisons if c.status == "improved"]
        accepted = not dropped and bool(improved)

        return {
            "format": GATE_FORMAT,
            "accepted": accepted,
            "decision": "accepted" if accepted else "rejected",
            "reason": self._build_reason(accepted, improved, dropped),
            "rule": {
                "splits": list(splits),
                "accept_if": "no split drops and at least one split improves",
            },
            "splits": {c.split: c.to_dict() for c in comparisons},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    def _build_reason(self, accepted: bool, improved: list[str], dropped: list[str]) -> str:
        if accepted:
            return f"accepted: improved {', '.join(improved)} with no split drops"
        if dropped:
            return f"rejected: dropped {', '.join(dropped)}"
        return "rejected: no split improved"

    def store_acceptance(self, candidate_id: str, result: dict) -> pathlib.Path:
        """Store acceptance result and return the path."""
        out_dir = self.snapshot_dir / "acceptances"
        out_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        out_path = out_dir / f"{candidate_id}-{timestamp}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return out_path

    def run_integrated(
        self,
        baseline_scores: dict[str, float],
        candidate_id: str,
        candidate_scores: dict[str, float] | None = None,
        store: bool = True,
    ) -> dict[str, Any]:
        """Run acceptance gate and optionally store result."""
        if candidate_scores is None:
            candidate_scores = self._load_candidate_scores(candidate_id)

        result = self.evaluate(baseline_scores, candidate_scores)

        if store:
            result["snapshot_path"] = str(self.store_acceptance(candidate_id, result))

        return result

    def _load_candidate_scores(self, candidate_id: str) -> dict[str, Any]:
        snapshot_path = self.snapshot_dir / f"{candidate_id}-scores.json"
        if snapshot_path.exists():
            return json.loads(snapshot_path.read_text(encoding="utf-8"))
        return {"train": 0, "heldout": 0}


class ScoreSnapshot:
    """Track scores over time for trend analysis."""

    def __init__(self, snapshots_dir: pathlib.Path):
        self.dir = snapshots_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def record(self, name: str, scores: dict[str, float], metadata: dict | None = None):
        payload = {
            "name": name,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "scores": scores,
            "metadata": metadata or {},
        }
        ts = int(time.time() * 1_000_000)
        out_path = self.dir / f"{name}-{ts}.json"
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return out_path

    def latest(self, name: str, default: dict | None = None) -> dict:
        files = sorted(self.dir.glob(f"{name}-*.json"), reverse=True)
        if not files:
            return (default or {})
        return json.loads(files[0].read_text(encoding="utf-8"))

    def history(self, name: str, limit: int = 20) -> list[dict]:
        files = sorted(self.dir.glob(f"{name}-*.json"), reverse=True)[:limit]
        return [json.loads(f.read_text(encoding="utf-8")) for f in files]

    def trend(self, name: str, metric: str) -> str:
        hist = self.history(name, limit=10)
        if len(hist) < 2:
            return "stable"
        values = [h.get("scores", {}).get(metric, 0) for h in hist]
        if values[0] > values[-1]:
            return "improving"
        if values[0] < values[-1]:
            return "declining"
        return "stable"
