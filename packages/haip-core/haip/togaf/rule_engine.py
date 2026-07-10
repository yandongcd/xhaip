"""Clinical Rule Engine — evaluates YAML-defined clinical rules against patient data.

Rule types: diagnosis, risk_score, treatment, followup, alert

Rule format (YAML):
  rule_type: diagnosis
  department: 内分泌科
  rules:
    - id: dm-diagnose-fpg
      condition:
        field: lab_results.FPG
        operator: ">="
        value: 7.0
      result:
        diagnosis: 糖尿病
        severity: 确诊
        recommendation: 复查OGTT确认

Operators: ==, !=, >=, <=, >, <, in, contains, regex
Condition combinators: and, or (arrays of sub-conditions)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import operator
import re


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent  # xhaip root
RULES_DIR = PROJECT_ROOT / "packages" / "haip-hospital" / "knowledge" / "rules"


@dataclass
class RuleMatch:
    rule_id: str
    rule_type: str
    department: str
    matched: bool
    result: dict[str, Any]
    description: str = ""


@dataclass
class PipelineResult:
    diagnosis: list[RuleMatch] = field(default_factory=list)
    risk_scores: list[RuleMatch] = field(default_factory=list)
    treatment: list[RuleMatch] = field(default_factory=list)
    followup: list[RuleMatch] = field(default_factory=list)
    alerts: list[RuleMatch] = field(default_factory=list)

    def summary(self) -> dict:
        def _best(matches: list[RuleMatch]) -> dict | None:
            if not matches:
                return None
            return matches[0].result
        return {
            "diagnosis": _best(self.diagnosis),
            "risk": _best(self.risk_scores),
            "treatment": _best(self.treatment),
            "followup": _best(self.followup),
            "alerts": [m.result for m in self.alerts[:5]],
        }


class RuleEngine:
    """Loads and evaluates clinical rules from YAML."""

    # Supported operators
    _OPS = {
        "==": operator.eq, "!=": operator.ne,
        ">=": operator.ge, "<=": operator.le,
        ">": operator.gt, "<": operator.lt,
    }

    def __init__(self, rules_dir: str | Path | None = None):
        self.rules_dir = Path(rules_dir) if rules_dir else RULES_DIR
        self._rules: dict[str, list[dict]] = {}  # dept → [rule_defs]
        self._loaded = False

    def load_all(self) -> int:
        """Load all YAML rule files from knowledge/rules/ (recursive)."""
        count = 0
        if not self.rules_dir.is_dir():
            return 0
        for yf in sorted(self.rules_dir.rglob("*.yaml")):
            if yf.name.startswith("_"):
                continue
            try:
                import yaml
                with open(yf, encoding="utf-8") as f:
                    # Handle multi-document YAML (--- separators)
                    docs = list(yaml.safe_load_all(f))
                for data in docs:
                    if not isinstance(data, dict):
                        continue
                    if "rules" not in data or "department" not in data:
                        continue
                    dept = data["department"]
                    self._rules.setdefault(dept, []).append(data)
                    count += 1
            except Exception:
                continue
        self._loaded = True
        return count

    def get_rules(self, department: str = "", rule_type: str = "") -> list[dict]:
        """Get rules filtered by department and/or rule type."""
        if not self._loaded:
            self.load_all()
        results: list[dict] = []
        for dept, rule_list in self._rules.items():
            if department and dept != department:
                continue
            for rule_def in rule_list:
                if rule_type and rule_def.get("rule_type") != rule_type:
                    continue
                results.append(rule_def)
        return results

    def evaluate(self, patient: dict, rule_type: str = "",
                 department: str = "") -> list[RuleMatch]:
        """Evaluate rules of given type against patient data."""
        rule_defs = self.get_rules(department=department, rule_type=rule_type)
        results: list[RuleMatch] = []
        for rule_def in rule_defs:
            dept = rule_def.get("department", "")
            for rule in rule_def.get("rules", []):
                matched, desc = self._check_condition(rule.get("condition", {}), patient)
                if matched:
                    results.append(RuleMatch(
                        rule_id=rule.get("id", "?"),
                        rule_type=rule_def.get("rule_type", "?"),
                        department=dept,
                        matched=True,
                        result=rule.get("result", {}),
                        description=desc,
                    ))
        return results

    def run_pipeline(self, patient: dict, department: str = "") -> PipelineResult:
        """Run full clinical pipeline: diagnosis→risk→treatment→followup→alert."""
        return PipelineResult(
            diagnosis=self.evaluate(patient, "diagnosis", department),
            risk_scores=self.evaluate(patient, "risk_score", department),
            treatment=self.evaluate(patient, "treatment", department),
            followup=self.evaluate(patient, "followup", department),
            alerts=self.evaluate(patient, "alert", department),
        )

    def _check_condition(self, condition: dict | list, patient: dict,
                         depth: int = 0) -> tuple[bool, str]:
        """Recursively evaluate a condition tree against patient data."""
        if depth > 10:
            return False, "max depth"

        # Combinator: AND
        if isinstance(condition, dict) and "and" in condition:
            subs = condition["and"]
            for sub in subs:
                ok, desc = self._check_condition(sub, patient, depth + 1)
                if not ok:
                    return False, f"AND failed: {desc}"
            return True, "all AND passed"

        # Combinator: OR
        if isinstance(condition, dict) and "or" in condition:
            subs = condition["or"]
            for sub in subs:
                ok, desc = self._check_condition(sub, patient, depth + 1)
                if ok:
                    return True, f"OR passed: {desc}"
            return False, "all OR failed"

        # Single condition
        if not isinstance(condition, dict):
            return False, "invalid condition"

        field_path = condition.get("field", "")
        op_str = condition.get("operator", "==")
        expected = condition.get("value")
        # Optional: severity markers
        actual = self._navigate(patient, field_path)

        if actual is None:
            return False, f"{field_path} not found"

        # String operators
        if op_str == "in":
            ok = actual in (expected if isinstance(expected, (list, str)) else str(expected))
            return ok, f"{field_path}={actual} in {expected}"
        if op_str == "contains":
            ok = str(expected).lower() in str(actual).lower()
            return ok, f"{field_path} contains '{expected}'"
        if op_str == "regex":
            try:
                ok = bool(re.search(str(expected), str(actual)))
                return ok, f"regex match: {field_path}"
            except re.error:
                return False, f"invalid regex: {expected}"

        # String equality (for == and != operators with non-numeric values)
        if op_str in ("==", "!="):
            try:
                float(actual)
                float(expected)
            except (ValueError, TypeError):
                # String comparison
                ok = (str(actual) == str(expected)) if op_str == "==" else (str(actual) != str(expected))
                return ok, f"{field_path}='{actual}' {op_str} '{expected}'"

        # Numeric comparison
        op_func = self._OPS.get(op_str)
        if op_func is None:
            return False, f"unknown operator: {op_str}"
        try:
            actual_num = float(actual)
            expected_num = float(expected)
            ok = op_func(actual_num, expected_num)
            return ok, f"{field_path}={actual} {op_str} {expected}"
        except (ValueError, TypeError):
            return False, f"type error: {field_path}={actual}"

    # Field alias mapping: rule path → patient data path fallbacks
    # When _navigate() can't find a value at the rule path, it tries these aliases.
    # Format: "rule_path_prefix" → [alternative_path, ...]
    _FIELD_ALIASES: dict[str, list[str]] = {
        # ECG → lab_results cardiac markers
        "ecg.ST_elevation_mm": ["lab_results.Troponin"],
        "ecg.Q_wave": ["lab_results.CK-MB"],
        # Vitals → lab_results or flat fields
        "vitals.pulse": ["lab_results.HR"],
        "vitals.respiration": ["lab_results.RR"],
        "vitals.temperature": ["lab_results.Temp"],
        "vitals.sbp": ["lab_results.SBP"],
        "vitals.dbp": ["lab_results.DBP"],
        "vitals.spo2": ["lab_results.SpO2"],
        # Neuro assessment → diagnosis or lab_results
        "neuro.face_droop": ["lab_results.FAST"],
        "neuro.gcs": ["lab_results.GCS_E"],
        # Assessment scores → lab_results
        "assessment.SOFA": ["lab_results.SOFA"],
        "assessment.MEWS": ["lab_results.MEWS"],
        "assessment.APACHE": ["lab_results.APACHE"],
        "assessment.ESI": ["lab_results.ESI"],
        # ECG findings → diagnosis
        "ecg.ST_elevation_lead": ["lab_results.ECG_lead", "diagnosis"],
        "ecg.rhythm": ["lab_results.ECG_rhythm", "diagnosis"],
    }

    @staticmethod
    def _navigate(data: dict, path: str) -> Any:
        """Navigate nested dict by dot-separated path, with field alias fallback."""
        if not path:
            return None
        parts = path.split(".")
        current: Any = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        # Return found value, or try alias fallback
        if current is not None:
            return current
        # Alias fallback: try alternative paths
        aliases = cls._FIELD_ALIASES.get(path, [])
        for alt_path in aliases:
            alt_parts = alt_path.split(".")
            alt_current: Any = data
            for part in alt_parts:
                if isinstance(alt_current, dict):
                    alt_current = alt_current.get(part)
                else:
                    alt_current = None
                    break
            if alt_current is not None:
                return alt_current
        return None


# ── TOGAF ABB Validation ──

@dataclass
class ABBValidationResult:
    rule_file: str
    department: str
    rule_type: str
    passed: bool = True
    issues: list[str] = field(default_factory=list)


def validate_all_rules(engine: RuleEngine | None = None) -> list[ABBValidationResult]:
    """Validate ABB traceability for all loaded rule groups."""
    if engine is None:
        engine = RuleEngine()
        engine.load_all()
    results: list[ABBValidationResult] = []
    for dept, rule_list in engine._rules.items():
        for rg in rule_list:
            v = ABBValidationResult(
                rule_file=f"{dept}/{rg.get('rule_type', '?')}",
                department=dept, rule_type=rg.get("rule_type", ""),
            )
            if not rg.get("capability"):
                v.passed = False
                v.issues.append("缺少 capability")
            if not rg.get("business_process"):
                v.passed = False
                v.issues.append("缺少 business_process")
            if not rg.get("data_entities"):
                v.passed = False
                v.issues.append("缺少 data_entities")
            if not rg.get("guideline"):
                v.passed = False
                v.issues.append("缺少 guideline")
            if not rg.get("stakeholder"):
                v.issues.append("缺 stakeholder (Phase A)")
            if not rg.get("version"):
                v.issues.append("缺 version (Phase H)")
            results.append(v)
    return results


def print_abb_report(results: list[ABBValidationResult] | None = None) -> str:
    if results is None:
        results = validate_all_rules()
    lines: list[str] = []
    passed = sum(1 for r in results if r.passed)
    lines.append(f"ABB Traceability: {passed}/{len(results)} passed")
    for r in results:
        s = "OK" if r.passed else "GAP"
        lines.append(f"  [{s}] {r.rule_file}")
        for i in r.issues:
            lines.append(f"       {i}")
    return "\n".join(lines)
