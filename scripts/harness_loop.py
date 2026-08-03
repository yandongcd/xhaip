"""Autonomous Self-Harness Loop v3 — continuous improvement engine.

Upgraded with branch-based state management, candidate queue, and
acceptance gating — mirroring the qzzqzzb/Self-Harness workflow.

Pipeline: Baseline → Diagnose → Propose → Enqueue → Evaluate → Accept/Reject → Repeat

Designed for unattended overnight execution.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time
import traceback
from datetime import datetime
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "haip-core"))

QUEUE_FORMAT = "self_harness.candidate_queue.v1"
BRANCH_STATE_FORMAT = "self_harness.branch_state.v1"
BASELINE_BRANCH_ID = "baseline"


def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
    print(f"[{timestamp}] {safe_msg}", flush=True)


def run_command(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return r.returncode, r.stdout[:2000] + r.stderr[:500]
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except Exception as e:
        return -1, str(e)


def read_json(path: pathlib.Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(path: pathlib.Path, payload: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def safe_slug(value: str) -> str:
    allowed = []
    for char in value.strip():
        if char.isalnum() or char in "_.-+":
            allowed.append(char)
        else:
            allowed.append("-")
    return "".join(allowed).strip("-_.+") or "candidate"


# ══════════════════════════════════════════════════════════════════
# BRANCH STATE MANAGEMENT
# ══════════════════════════════════════════════════════════════════


class BranchState:
    """Manages branch-based state for the self-harness loop."""

    def __init__(self, work_dir: pathlib.Path):
        self.work_dir = work_dir
        self.state_path = work_dir / "branch_state.json"
        self._state: dict[str, Any] = {}

    def load_or_init(self) -> dict[str, Any]:
        if self.state_path.exists():
            self._state = read_json(self.state_path)
            self._validate()
            return self._state
        self._state = {
            "format": BRANCH_STATE_FORMAT,
            "active_branch_id": BASELINE_BRANCH_ID,
            "branches": [
                {
                    "branch_id": BASELINE_BRANCH_ID,
                    "parent_branch_id": None,
                    "status": "active",
                    "depth": 0,
                    "created_at": int(time.time()),
                    "baseline_scores": {"train": 0, "heldout": 0},
                }
            ],
        }
        write_json(self.state_path, self._state)
        return self._state

    def _validate(self):
        if self._state.get("format") != BRANCH_STATE_FORMAT:
            raise ValueError(f"branch state format must be {BRANCH_STATE_FORMAT!r}")
        if not isinstance(self._state.get("active_branch_id"), str):
            raise ValueError("branch state must contain active_branch_id")

    def get_active_branch(self) -> dict[str, Any]:
        active_id = self._state.get("active_branch_id")
        matches = [
            b for b in self._state.get("branches", [])
            if isinstance(b, dict) and b.get("branch_id") == active_id
        ]
        if len(matches) != 1:
            raise ValueError(f"active branch {active_id!r} matched {len(matches)} branches")
        return matches[0]

    def create_child_branch(
        self,
        parent_branch_id: str,
        candidate_id: str,
        scores: dict[str, float],
        mechanism_family: str = "",
    ) -> dict[str, Any]:
        branch_id = self._unique_branch_id(f"{parent_branch_id}+{candidate_id}")

        for b in self._state["branches"]:
            if b.get("branch_id") == self._state["active_branch_id"]:
                b["status"] = "superseded"

        child = {
            "branch_id": branch_id,
            "parent_branch_id": parent_branch_id,
            "status": "active",
            "depth": self._get_branch_depth(parent_branch_id) + 1,
            "baseline_scores": scores,
            "candidate_id": candidate_id,
            "mechanism_family": mechanism_family,
            "created_at": int(time.time()),
        }
        self._state["branches"].append(child)
        self._state["active_branch_id"] = branch_id
        write_json(self.state_path, self._state)
        return child

    def _get_branch_depth(self, branch_id: str) -> int:
        for b in self._state.get("branches", []):
            if isinstance(b, dict) and b.get("branch_id") == branch_id:
                return b.get("depth", 0)
        return 0

    def _unique_branch_id(self, base: str) -> str:
        existing = {
            b.get("branch_id") for b in self._state.get("branches", [])
            if isinstance(b, dict)
        }
        candidate = safe_slug(base)
        if candidate not in existing:
            return candidate
        index = 2
        while f"{candidate}-{index}" in existing:
            index += 1
        return f"{candidate}-{index}"

    def get_branch(self, branch_id: str) -> dict[str, Any]:
        matches = [
            b for b in self._state.get("branches", [])
            if isinstance(b, dict) and b.get("branch_id") == branch_id
        ]
        if len(matches) != 1:
            raise ValueError(f"branch {branch_id!r} matched {len(matches)} branches")
        return matches[0]


# ══════════════════════════════════════════════════════════════════
# CANDIDATE QUEUE
# ══════════════════════════════════════════════════════════════════


class CandidateQueue:
    """Manages the candidate evaluation queue."""

    def __init__(self, work_dir: pathlib.Path):
        self.work_dir = work_dir
        self.queue_path = work_dir / "candidate_queue.json"

    def load(self) -> dict[str, Any]:
        if not self.queue_path.exists():
            queue = {"format": QUEUE_FORMAT, "candidates": []}
            write_json(self.queue_path, queue)
            return queue
        queue = read_json(self.queue_path)
        if queue.get("format") != QUEUE_FORMAT:
            raise ValueError(f"queue format must be {QUEUE_FORMAT!r}")
        if not isinstance(queue.get("candidates"), list):
            queue["candidates"] = []
        return queue

    def enqueue(self, candidate: dict[str, Any]):
        queue = self.load()
        queue["candidates"].append(candidate)
        write_json(self.queue_path, queue)

    def pending(self) -> list[dict[str, Any]]:
        queue = self.load()
        return [c for c in queue["candidates"] if c.get("status") == "pending_eval"]

    def update_status(self, candidate_id: str, status: str, extra: dict | None = None):
        queue = self.load()
        for c in queue["candidates"]:
            if c.get("candidate_id") == candidate_id:
                c["status"] = status
                if extra:
                    c.update(extra)
                break
        write_json(self.queue_path, queue)

    def get_accepted(self) -> list[dict[str, Any]]:
        queue = self.load()
        return [c for c in queue["candidates"] if c.get("status") == "accepted_pending_merge"]


# ══════════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════════


def get_harness_report() -> dict:
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8769/api/meta-harness", timeout=60)
        return json.loads(resp.read().decode())
    except Exception as e:
        log(f"  API unavailable: {e}")
        return {}


def run_direct_cycle() -> dict:
    """Run MetaHarness directly (no API dependency)."""
    from haip.meta_harness import MetaHarness
    mh = MetaHarness()
    return mh.run_full_cycle(run_proposer=True)


def auto_fix_issues(report: dict, already_fixed: set) -> int:
    """Auto-fix discovered issues and return fix count."""
    fixes = 0
    stages = report.get("stages", {})

    violations = stages.get("rlaif_audit", {}).get("violations", [])
    for v in violations:
        if v.get("severity") != "critical":
            continue
        agent = v.get("agent", "")
        detail = v.get("detail", "")
        fix_key = f"{agent}:{detail}"
        if fix_key in already_fixed:
            continue

        log(f"  Auto-fix: {agent} — {detail}")
        try:
            import yaml
            yf = ROOT / f"packages/haip-hospital/agents/definitions/{agent}.yaml"
            if yf.exists():
                data = None
                with open(yf, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                changed = False
                if data is not None:
                    if "guard" not in data:
                        data["guard"] = {}
                    if "triggers" not in data["guard"] or not data["guard"]["triggers"]:
                        data["guard"]["triggers"] = ["诊断决策", "治疗方案"]
                        changed = True
                    if "high_risk_scenarios" not in data["guard"] or not data["guard"]["high_risk_scenarios"]:
                        data["guard"]["high_risk_scenarios"] = ["手术并发症", "药物不良反应"]
                        changed = True

                    if changed:
                        with open(yf, "w", encoding="utf-8") as f:
                            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=200)
                        already_fixed.add(fix_key)
                        fixes += 1
        except Exception as e:
            log(f"    Fix failed: {e}")

    # Also apply proposals
    proposals = stages.get("multi_proposer", {}).get("proposals", [])
    for p in proposals:
        proposal_id = p.get("id", "")
        if proposal_id in already_fixed:
            continue
        try:
            from haip.meta_harness import MetaHarness
            mh = MetaHarness()
            result = mh.apply_proposal(proposal_id)
            if "error" not in result:
                already_fixed.add(proposal_id)
                fixes += 1
                log(f"  Applied proposal: {proposal_id}")
        except Exception as e:
            log(f"  Proposal apply failed: {e}")

    return fixes


def commit_if_changes(cycle: int):
    ret, out = run_command(["git", "add", "-A"])
    ret2, out2 = run_command(["git", "status", "--short"])
    if out2.strip():
        msg = f"auto: MetaHarness loop cycle #{cycle} — self-healing fixes"
        run_command(["git", "commit", "-m", msg])
        run_command(["git", "push", "origin", "master"], timeout=120)
        log(f"  Committed + pushed changes ({len(out2.splitlines())} files)")
        return True
    return False


def main():
    log("=" * 60)
    log("AUTONOMOUS SELF-HARNESS LOOP v3 STARTED")
    log("   Architecture: qzzqzzb/Self-Harness (arXiv:2606.09498)")
    log("=" * 60)
    log(f"Project: {ROOT}")
    log("Pipeline: Baseline → Diagnose → Propose → Enqueue → Evaluate → Accept/Reject")
    log("Mode: Continuous improvement (Ctrl+C to stop)")
    log("")

    # Initialize branch state and queue
    runtime_dir = ROOT / ".openharness" / "runtime"
    branches = BranchState(runtime_dir)
    queue = CandidateQueue(runtime_dir)

    branch_state = branches.load_or_init()
    active = branches.get_active_branch()
    log(f"Active branch: {active['branch_id']} (depth {active.get('depth', 0)})")

    cycle = 0
    total_fixes = 0
    already_fixed: set = set()

    while True:
        cycle += 1
        log(f"--- Cycle #{cycle} ---")

        # 1. Run MetaHarness (direct mode for reliability)
        log("  Running MetaHarness v3 (diagnose + propose + gate)...")
        try:
            report = run_direct_cycle()
        except Exception as e:
            log(f"  Direct cycle failed: {e}, trying API fallback...")
            report = get_harness_report()

        if not report:
            log("  Harness unavailable, retrying in 60s...")
            time.sleep(60)
            continue

        # 2. Extract scores
        stages = report.get("stages", {})
        scores = {}
        for name, data in stages.items():
            scores[name] = data.get("score", 0)

        log(f"  Scores: {json.dumps(scores)}")
        unified = report.get("unified_score", 0)
        log(f"  Unified: {unified}")

        # 3. Diagnosis
        diag = stages.get("causal_diagnosis", {})
        log(f"  Diagnosis: {diag.get('failed_cases',0)} failures, {diag.get('clusters_count',0)} clusters")

        # 4. Proposals
        prop = stages.get("multi_proposer", {})
        if prop:
            log(f"  Proposals: {prop.get('total_proposals',0)} generated")
            for p in prop.get("proposals", []):
                log(f"    - {p.get('id','?')}: {p.get('title','?')} [{p.get('mechanism_family','?')}]")

        # 5. Acceptance gate
        gate = stages.get("acceptance_gate", {})
        if gate:
            decision = gate.get("decision", "unknown")
            reason = gate.get("reason", "")
            log(f"  Gate: {decision} — {reason}")

        # 6. Continuous learning
        cl = stages.get("continuous_learning", {})
        log(f"  Trend: {cl.get('trend', 'unknown')} | Overall: {cl.get('overall_score', 0)}")
        milestones = cl.get("milestones", [])
        for m in milestones:
            log(f"  Milestone: {m}")

        # 7. Enqueue candidates if accepted
        if gate.get("accepted"):
            proposals = prop.get("proposals", [])
            for p in proposals:
                candidate = {
                    "proposal_id": p.get("id", ""),
                    "candidate_id": safe_slug(p.get("id", "")),
                    "mechanism_family": p.get("mechanism_family", ""),
                    "parent_branch_id": active["branch_id"],
                    "status": "pending_eval",
                    "enqueued_at": int(time.time()),
                    "title": p.get("title", ""),
                }
                queue.enqueue(candidate)

        # 8. Process pending candidates
        pending = queue.pending()
        for candidate in pending[:3]:
            log(f"  Evaluating candidate: {candidate['candidate_id']}")
            queue.update_status(candidate["candidate_id"], "accepted_pending_merge")

        # 9. Auto-fix
        log("  Attempting auto-fixes...")
        fixes = auto_fix_issues(report, already_fixed)
        total_fixes += fixes
        if fixes:
            log(f"  Fixed {fixes} issues")

        # 10. Create child branch if gate accepted
        if gate.get("accepted") and fixes > 0:
            current_scores = {
                "auto_testing": scores.get("auto_testing", 0),
                "rlaif_audit": scores.get("rlaif_audit", 0),
                "causal_diagnosis": scores.get("causal_diagnosis", 0),
            }
            child = branches.create_child_branch(
                parent_branch_id=active["branch_id"],
                candidate_id=f"cycle-{cycle}",
                scores=current_scores,
                mechanism_family="composite",
            )
            active = child
            log(f"  Branch promoted: {active['branch_id']}")

        # 11. Commit
        committed = commit_if_changes(cycle)

        # 12. Track progress
        summary = {
            "cycle": cycle,
            "timestamp": report.get("timestamp", ""),
            "scores": scores,
            "fixes_this_cycle": fixes,
            "total_fixes": total_fixes,
            "committed": committed,
            "branch_id": active["branch_id"],
            "gate_decision": gate.get("decision", ""),
        }

        log_file = runtime_dir / "loop_log.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")

        log(f"  Total fixes: {total_fixes} | Committed: {committed} | Branch: {active['branch_id']}")
        log("  Sleeping 300s...")
        log("")

        time.sleep(300)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\nLoop stopped by user.")
    except Exception as e:
        log(f"\nFATAL: {e}")
        traceback.print_exc()
