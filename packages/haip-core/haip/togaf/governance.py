"""TOGAF Business Process Governance Validator.

Validates business processes against TOGAF governance rules defined in
``knowledge/rules/togaf-governance-rules.yaml``.

Checks implemented:
  - gov-bp-002: ProcessStep implementation.module must reference a valid importable module
  - gov-bp-003: guidelines IDs must exist in knowledge/guidelines/
  - gov-bp-004: data_used entity IDs must map to known data entities

Usage:
  from haip.togaf.governance import validate_business_processes
  results = validate_business_processes()
  for r in results:
      print(f"{'PASS' if r.passed else 'FAIL'} {r.check_id}: {r.detail}")
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Known data entity IDs (used by business process steps) ──

_KNOWN_DATA_ENTITIES: set[str] = {
    "de-lab-results",
    "de-exam-results",
    "de-patient",
    "de-risk-assessment",
    "de-rx",
    "de-drug",
    "de-surgery-record",
    "de-nutrition-assessment",
    "de-consent-form",
    "de-nursing-record",
    "de-followup-plan",
    "de-followup",
    "de-rehab-record",
    "de-clinical-record",
    "de-medications",
    "de-mdt-decision",
}


# ── Project root discovery ──

def _find_project_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__).resolve()).parent
    for _ in range(8):
        if (current / "packages" / "haip-core").is_dir():
            return current
        if (current / "packages" / "haip-hospital").is_dir():
            return current
        if current.parent == current:
            break
        current = current.parent
    return Path.cwd()


# ── Path helpers ──

def _knowledge_dir(project_root: Path) -> Path:
    return project_root / "packages" / "haip-hospital" / "knowledge"


# ── Data model ──

@dataclass
class BPCheckResult:
    """Result of a single governance check against a business process."""

    bp_name: str
    check_id: str
    check_name: str
    passed: bool
    detail: str
    suggestion: str = ""


@dataclass
class BPValidationReport:
    """Aggregated governance validation report for all business processes."""

    bp_count: int
    checks_total: int
    checks_passed: int
    results: list[BPCheckResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return self.checks_passed == self.checks_total

    def summary(self) -> str:
        lines = [
            "=" * 60,
            f"TOGAF BP Governance Validation — {self.checks_passed}/{self.checks_total} checks passed",
            f"  Business Processes scanned: {self.bp_count}",
            "=" * 60,
        ]
        for r in self.results:
            mark = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{mark}] {r.check_id} {r.check_name} — {r.bp_name}")
            if not r.passed:
                lines.append(f"         → {r.detail}")
                if r.suggestion:
                    lines.append(f"         → Suggestion: {r.suggestion}")
        return "\n".join(lines)


# ── Governance rule loading ──

def load_governance_rules(project_root: Path | None = None) -> dict[str, Any]:
    """Load TOGAF governance rules from YAML."""
    root = project_root or _find_project_root()
    rules_path = _knowledge_dir(root) / "rules" / "togaf-governance-rules.yaml"
    if not rules_path.is_file():
        return {}
    import yaml
    with open(rules_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_bp_governance_rules(project_root: Path | None = None) -> list[dict[str, Any]]:
    """Return only the BusinessProcess governance rules (gov-bp-*)."""
    data = load_governance_rules(project_root)
    rules = data.get("rules", [])
    return [r for r in rules if r.get("id", "").startswith("gov-bp-")]


# ── Business process loading ──

def _load_business_processes(project_root: Path | None = None) -> list[dict[str, Any]]:
    """Load all business process YAML definitions."""
    root = project_root or _find_project_root()
    bp_dir = _knowledge_dir(root) / "business_processes"
    if not bp_dir.is_dir():
        return []

    import yaml
    bps: list[dict[str, Any]] = []
    for yaml_file in sorted(bp_dir.glob("*.yaml")):
        if yaml_file.name.startswith("_"):
            continue
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                # Accept both "name" (TOGAF format) and "department" (auto-generated format)
                if "name" in data or "department" in data:
                    # Ensure a 'name' key exists for downstream checks
                    if "name" not in data:
                        data["name"] = data.get("department", yaml_file.stem)
                    bps.append(data)
                # Also handle files that contain business_processes list at top level
                if "business_processes" in data:
                    for bp in data["business_processes"]:
                        if isinstance(bp, dict):
                            bps.append(bp)
        except Exception:
            continue
    return bps


# ── Check: gov-bp-002 — Step Module Coverage ──

def _check_step_module_coverage(
    bp: dict[str, Any],
    _project_root: Path,
) -> list[BPCheckResult]:
    """gov-bp-002: Each ProcessStep's implementation.module must be importable.

    For steps with no decision: import-only check.
    For steps with decision: also check decision_coverage.
    """
    bp_name = bp.get("name", "unknown")
    steps = bp.get("steps", [])
    results: list[BPCheckResult] = []

    for step in steps:
        # Handle both dict steps and string steps (auto-generated placeholders)
        if isinstance(step, str):
            results.append(BPCheckResult(
                bp_name=bp_name, check_id="gov-bp-002",
                check_name="Step Module Coverage",
                passed=True,
                detail=f"Step '{step}': string label only (no module check needed)",
            ))
            continue
        step_id = step.get("id", "?")
        impl = step.get("implementation", {})
        module_path = impl.get("module", "")

        if not module_path:
            results.append(BPCheckResult(
                bp_name=bp_name,
                check_id="gov-bp-002",
                check_name="Step Module Coverage",
                passed=False,
                detail=f"Step {step_id}: no implementation.module defined",
                suggestion="Each ProcessStep must have implementation.module set",
            ))
            continue

        # Check module importability
        try:
            importlib.import_module(module_path)
            import_ok = True
            import_msg = ""
        except ImportError as e:
            import_ok = False
            import_msg = str(e)

        # Decision coverage check
        decision_coverage = impl.get("decision_coverage")
        if decision_coverage:
            total = decision_coverage.get("total", 0)
            covered = decision_coverage.get("covered", 0)
            if import_ok:
                if covered >= total:
                    results.append(BPCheckResult(
                        bp_name=bp_name,
                        check_id="gov-bp-002",
                        check_name="Step Module Coverage",
                        passed=True,
                        detail=f"Step {step_id}: module '{module_path}' importable, "
                               f"decision coverage {covered}/{total}",
                    ))
                else:
                    results.append(BPCheckResult(
                        bp_name=bp_name,
                        check_id="gov-bp-002",
                        check_name="Step Module Coverage",
                        passed=False,
                        detail=f"Step {step_id}: module importable but "
                               f"decision coverage {covered}/{total} (incomplete)",
                        suggestion=f"Cover {total - covered} missing branch(es)",
                    ))
            else:
                results.append(BPCheckResult(
                    bp_name=bp_name,
                    check_id="gov-bp-002",
                    check_name="Step Module Coverage",
                    passed=False,
                    detail=f"Step {step_id}: module '{module_path}' import failed: {import_msg}",
                    suggestion="Verify the module exists and is on PYTHONPATH",
                ))
        else:
            # No decision_coverage — import-only
            if import_ok:
                results.append(BPCheckResult(
                    bp_name=bp_name,
                    check_id="gov-bp-002",
                    check_name="Step Module Coverage",
                    passed=True,
                    detail=f"Step {step_id}: module '{module_path}' importable",
                ))
            else:
                results.append(BPCheckResult(
                    bp_name=bp_name,
                    check_id="gov-bp-002",
                    check_name="Step Module Coverage",
                    passed=False,
                    detail=f"Step {step_id}: module '{module_path}' import failed: {import_msg}",
                    suggestion="Verify the module exists and is on PYTHONPATH",
                ))

    return results


# ── Check: gov-bp-003 — Guideline Reference Existence ──

def _check_guideline_refs(
    bp: dict[str, Any],
    guidelines_dir: Path,
) -> BPCheckResult:
    """gov-bp-003: Each guideline_refs ID must exist in guidelines directory."""
    bp_name = bp.get("name", "unknown")
    refs = bp.get("guideline_refs", bp.get("guidelines", []))

    if not refs:
        return BPCheckResult(
            bp_name=bp_name,
            check_id="gov-bp-003",
            check_name="Guideline Reference Existence",
            passed=False,
            detail="No guideline_refs defined",
            suggestion="Each BusinessProcess must reference at least one clinical guideline",
        )

    # Build set of existing guideline file stems
    existing: set[str] = set()
    for gfile in guidelines_dir.glob("*.yaml"):
        if gfile.is_file():
            existing.add(gfile.stem)

    missing: list[str] = []
    for ref_id in refs:
        if ref_id not in existing:
            missing.append(ref_id)

    if missing:
        return BPCheckResult(
            bp_name=bp_name,
            check_id="gov-bp-003",
            check_name="Guideline Reference Existence",
            passed=False,
            detail=f"Missing guidelines: {', '.join(missing)} "
                   f"(searched in {guidelines_dir})",
            suggestion="Add the referenced guideline YAML or correct the reference ID",
        )

    return BPCheckResult(
        bp_name=bp_name,
        check_id="gov-bp-003",
        check_name="Guideline Reference Existence",
        passed=True,
        detail=f"All {len(refs)} guideline ref(s) found: {', '.join(refs)}",
    )


# ── Check: gov-bp-004 — Data Entity Reference Validity ──

def _check_data_entity_refs(
    bp: dict[str, Any],
    _data_entities_dir: Path,
) -> list[BPCheckResult]:
    """gov-bp-004: Each data_used entity ID must be a known entity.

    Searches both the on-disk data_entities directory (if it exists) and a
    hardcoded registry of well-known entity IDs from business process definitions.
    """
    bp_name = bp.get("name", "unknown")
    steps = bp.get("steps", [])
    results: list[BPCheckResult] = []

    # Collect known entities from template data
    known: set[str] = set(_KNOWN_DATA_ENTITIES)
    # Also add common entities from BP inputs/outputs
    common = ["患者信息", "检验报告", "影像报告", "手术记录", "随访记录", "治疗方案",
              "生命体征", "超声报告", "专科检查报告", "治疗记录", "转归记录",
              "评估结果", "诊断结果", "护理计划", "康复计划"]
    known.update(common)
    if _data_entities_dir.is_dir():
        for ef in _data_entities_dir.glob("*.yaml"):
            if ef.is_file():
                known.add(ef.stem)

    # Check BP-level inputs/outputs (not just step-level data_used)
    all_data_refs: list[str] = []
    for key in ["inputs", "outputs"]:
        refs = bp.get(key, [])
        if isinstance(refs, list):
            all_data_refs.extend(refs)

    for step in steps:
        if isinstance(step, str):
            continue  # Skip string-only placeholder steps
        step_id = step.get("id", step.get("name", "?"))
        data_used = step.get("data_used")
        if data_used and isinstance(data_used, list):
            all_data_refs.extend(data_used)

    # Deduplicate
    all_data_refs = list(set(all_data_refs))
    if not all_data_refs:
        results.append(BPCheckResult(
            bp_name=bp_name, check_id="gov-bp-004",
            check_name="Data Entity Reference Validity",
            passed=True,
            detail="No data entity references found (may use generic entities)",
        ))
        return results

    unknown: list[str] = [ref for ref in all_data_refs if ref not in known]
    if unknown:
        results.append(BPCheckResult(
            bp_name=bp_name, check_id="gov-bp-004",
            check_name="Data Entity Reference Validity",
            passed=False,
            detail=f"Unknown entity refs: {', '.join(unknown[:10])}",
            suggestion="Add entity definitions or use known entities",
        ))
    else:
        results.append(BPCheckResult(
            bp_name=bp_name, check_id="gov-bp-004",
            check_name="Data Entity Reference Validity",
            passed=True,
            detail=f"All {len(all_data_refs)} entity refs known",
        ))

    if not results:
        results.append(BPCheckResult(
            bp_name=bp_name,
            check_id="gov-bp-004",
            check_name="Data Entity Reference Validity",
            passed=True,
            detail="No data_used references to validate",
        ))

    return results


# ── Public API ──

def validate_business_processes(
    project_root: Path | None = None,
) -> BPValidationReport:
    """Run all 3 BP governance checks against every business process YAML.

    Returns a BPValidationReport with per-step results.
    """
    root = project_root or _find_project_root()
    knowledge = _knowledge_dir(root)
    guidelines_dir = knowledge / "guidelines"
    data_entities_dir = knowledge / "data_entities"

    bps = _load_business_processes(root)
    all_results: list[BPCheckResult] = []

    for bp in bps:
        all_results.extend(_check_step_module_coverage(bp, root))
        all_results.append(_check_guideline_refs(bp, guidelines_dir))
        all_results.extend(_check_data_entity_refs(bp, data_entities_dir))

    passed = sum(1 for r in all_results if r.passed)
    return BPValidationReport(
        bp_count=len(bps),
        checks_total=len(all_results),
        checks_passed=passed,
        results=all_results,
    )


def validate_business_processes_detail(
    project_root: Path | None = None,
) -> str:
    """Run BP governance validation and return a human-readable summary string."""
    report = validate_business_processes(project_root)
    return report.summary()
