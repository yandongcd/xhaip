"""KnowledgeAgent — Base class for clinically-intelligent Agent handlers.

Provides:
  - Guideline lookup by diagnosis / department
  - Rule-based decision support
  - Patient data enrichment
  - Structured clinical reasoning output

Usage:
  from haip.togaf.knowledge_agent import KnowledgeAgent

  class RespiratoryAgent(KnowledgeAgent):
      def bp_reception(self, patient_id):
          patient = self.get_patient(patient_id)
          guides = self.search_guidelines("COPD")
          return self.clinical_result("评估完成", patient, guides)
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent  # xhaip root
KNOWLEDGE_DIR = Path(os.environ.get(
    "HAIP_KNOWLEDGE_DIR",
    str(PROJECT_ROOT / "packages" / "haip-hospital" / "knowledge"),
))
PATIENTS_FILE = Path(os.environ.get(
    "HAIP_PATIENTS_FILE",
    str(PROJECT_ROOT / "packages" / "haip-hospital" / "data" / "patients.json"),
))

# Cached patient data (mtime+size invalidation, thread-safe)
_patient_cache: dict[str, dict] | None = None
_patient_cache_mtime: float = -1.0
_patient_cache_size: int = -1
_patient_cache_lock = threading.Lock()


def clear_patient_cache() -> None:
    """清空患者缓存 (测试/数据更新后调用)。"""
    global _patient_cache, _patient_cache_mtime, _patient_cache_size
    with _patient_cache_lock:
        _patient_cache = None
        _patient_cache_mtime = -1.0
        _patient_cache_size = -1


def _load_patients() -> dict[str, dict]:
    global _patient_cache, _patient_cache_mtime, _patient_cache_size
    with _patient_cache_lock:
        if PATIENTS_FILE.exists():
            try:
                st = PATIENTS_FILE.stat()
                current = (st.st_mtime, st.st_size)
            except OSError:
                current = None
        else:
            current = None

        # Rebuild if cache absent, or file changed since last load
        stale = (
            current is None
            or _patient_cache is None
            or _patient_cache_mtime != current[0]
            or _patient_cache_size != current[1]
        )
        if stale:
            _patient_cache = {}
            if PATIENTS_FILE.exists():
                with open(PATIENTS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                for p in data.get("patients", []):
                    _patient_cache[p["patient_id"]] = p
            if current is not None:
                _patient_cache_mtime, _patient_cache_size = current
            else:
                _patient_cache_mtime, _patient_cache_size = -1.0, -1
        return _patient_cache or {}


class KnowledgeAgent:
    """Base class for handlers with knowledge-aware clinical reasoning."""

    agent_name: str = ""
    department: str = ""
    guidelines_cache: list[dict] = []
    _rule_engine: object | None = None  # RuleEngine instance (lazy loaded)

    def __init__(self, agent_name: str = "", department: str = ""):
        self.agent_name = agent_name
        self.department = department

    @property
    def rule_engine(self):
        """Lazy-load RuleEngine on first access."""
        if self._rule_engine is None:
            from haip.togaf.rule_engine import RuleEngine
            self._rule_engine = RuleEngine()
        return self._rule_engine

    def run_clinical_pipeline(self, patient: dict) -> object:
        """Run full clinical pipeline (diagnosis→risk→treatment→alerts) via RuleEngine."""
        return self.rule_engine.run_pipeline(patient, department=self.department)

    def clinical_result_from_pipeline(self, patient: dict,
                                       pipeline_result: object = None) -> dict:
        """Generate clinical_result using RuleEngine pipeline output."""
        if pipeline_result is None:
            pipeline_result = self.run_clinical_pipeline(patient)
        s = pipeline_result.summary()
        diag = s.get("diagnosis", {})
        risk = s.get("risk", {})
        treatment = s.get("treatment", {})
        alerts = s.get("alerts", [])

        summary_parts = []
        if diag:
            summary_parts.append(f"{diag.get('diagnosis', '')} ({diag.get('severity', '')})")
        if risk:
            summary_parts.append(f"风险: {risk.get('risk', '')}")
        if treatment:
            summary_parts.append(f"方案: {treatment.get('treatment', '')[:30]}")

        result: dict[str, Any] = {
            "status": "ok",
            "agent": self.agent_name,
            "summary": " | ".join(summary_parts) if summary_parts else "评估完成",
        }
        if patient:
            result["patient"] = {
                "id": patient.get("patient_id"),
                "name": patient.get("name"),
                "diagnosis": patient.get("diagnosis"),
            }
        if diag:
            result["diagnosis"] = diag
        if risk:
            result["risk"] = risk
        if treatment:
            result["treatment"] = treatment
        if alerts:
            result["alerts"] = [a.get("message", str(a)) for a in alerts]
        return result

    def get_patient(self, patient_id: str) -> dict | None:
        return _load_patients().get(patient_id)

    def get_patients_by_dept(self) -> list[dict]:
        dept = self.department
        return [p for p in _load_patients().values()
                if p.get("department") == dept]

    def get_patient_from_kwargs(self, kwargs: dict) -> tuple[dict | None, dict | None]:
        """从 kwargs 提取 patient_id 并查找患者。返回 (patient, error_dict)。"""
        pid = kwargs.get("patient_id", "")
        p = self.get_patient(pid)
        if not p:
            return None, {"status": "error", "agent": self.agent_name, "error": f"Patient {pid} not found"}
        return p, None

    def make_clinical_error(self, msg: str) -> dict:
        """构建统一的 clinical error 响应字典。"""
        return {"status": "error", "agent": self.agent_name, "error": msg}

    def search_guidelines(self, query: str) -> list[str]:
        """Search knowledge/guidelines/ for relevant guidelines.

        Returns matching guideline file stems (content keyword match).
        """
        guidelines_dir = KNOWLEDGE_DIR / "guidelines"
        results: list[str] = []
        if not guidelines_dir.exists():
            return results
        q = query.lower()
        for f in sorted(guidelines_dir.glob("*.yaml")):
            try:
                with open(f, encoding="utf-8") as fh:
                    content = fh.read()
                if q in content.lower():
                    results.append(f.stem)
            except Exception:
                logger.debug("Guideline file search failed: %s", f, exc_info=True)
        return results[:10]

    def search_rules(self, query: str = "") -> list[str]:
        """Search loaded clinical rules and return rule reference strings.

        Matching strategy:
          1. exact department match (query == rule department)
          2. substring match (query inside rule department name)
          3. fall back to this agent's department when query is empty/unmatched
        Returns e.g. "消化内科/diagnosis/R1-01" references for rule_refs display.
        """
        try:
            engine = self.rule_engine
            q = (query or "").strip()
            docs = engine.get_rules(department=q) if q else []
            if not docs and q:
                all_docs = engine.get_rules()
                docs = [d for d in all_docs if q in str(d.get("department", ""))]
            if not docs and self.department:
                docs = engine.get_rules(department=self.department)
                if not docs:
                    all_docs = engine.get_rules()
                    docs = [d for d in all_docs
                            if self.department in str(d.get("department", ""))]
            refs: list[str] = []
            for d in docs:
                dept_name = str(d.get("department", ""))
                rtype = str(d.get("rule_type", ""))
                rules = d.get("rules", []) or []
                for r in rules:
                    rid = str(r.get("id", "")) if isinstance(r, dict) else ""
                    refs.append(f"{dept_name}/{rtype}/{rid}" if rid else f"{dept_name}/{rtype}")
                if not rules:
                    refs.append(f"{dept_name}/{rtype}")
            return refs[:20]
        except Exception:
            logger.debug("Rule search failed for %r", query, exc_info=True)
            return []

    def assess_vitals(self, patient: dict) -> dict:
        """Basic vital sign assessment from patient data."""
        labs = patient.get("lab_results", {})
        alerts: list[str] = []

        for key, (low, high, unit) in _VITAL_RANGES.items():
            val = labs.get(key)
            if val is not None:
                try:
                    v = float(val)
                    if v < low:
                        alerts.append(f"{key}偏低({v}{unit})")
                    elif v > high:
                        alerts.append(f"{key}偏高({v}{unit})")
                except (ValueError, TypeError):
                    pass

        return {"alerts": alerts, "all_normal": len(alerts) == 0}

    def clinical_result(self, summary: str | dict = "",
                        patient: dict | None = None,
                        guidelines: list[str] | None = None,
                        rules: list[str] | None = None,
                        alerts: list[str] | None = None,
                        **kwargs: Any) -> dict:
        """Generate structured clinical reasoning result.

        Backward-compatible: accepts clinical_result(summary_str, patient=...)
        or clinical_result(patient=patient_obj, summary=...,
                           stage=..., findings=..., recommendations=...,
                           guideline_refs=...)
        """
        # Backward compat: if first arg is a dict, treat as patient
        actual_patient = patient
        actual_summary = ""
        if isinstance(summary, dict):
            actual_patient = summary
        else:
            actual_summary = summary

        result: dict[str, Any] = {
            "status": "ok",
            "agent": self.agent_name,
        }
        if actual_summary:
            result["summary"] = actual_summary

        stage = kwargs.get("stage", "")
        if stage:
            result["stage"] = stage
        findings = kwargs.get("findings")
        if findings:
            result["findings"] = findings
        recommendations = kwargs.get("recommendations")
        if recommendations:
            result["recommendations"] = recommendations

        if actual_patient:
            result["patient"] = {
                "id": actual_patient.get("patient_id"),
                "name": actual_patient.get("name"),
                "diagnosis": actual_patient.get("diagnosis"),
            }
            if alerts is None:
                vitals = self.assess_vitals(actual_patient)
                alerts = vitals.get("alerts", [])
        refs = kwargs.get("guideline_refs") or guidelines or []
        if refs:
            result["guideline_refs"] = refs
        if rules:
            result["rule_refs"] = rules
        if alerts:
            result["alerts"] = alerts
        return result


# Common vital sign / lab reference ranges
# Primary source: knowledge/rules/reference_ranges.yaml
# Falls back to hardcoded defaults if YAML not available.
# NOTE: These are REFERENCE RANGES (normal range), distinct from CRITICAL VALUES
# defined in knowledge/rules/clinical_lab_critical_value/critical_thresholds.yaml
_VITAL_RANGES_DEFAULTS: dict[str, tuple[float, float, str]] = {
    "Hb": (110, 160, "g/L"),
    "WBC": (3.5, 10.0, "x10^9/L"),
    "PLT": (100, 300, "x10^9/L"),
    "CRP": (0, 10, "mg/L"),
    "Cr": (60, 110, "umol/L"),
    "ALT": (10, 40, "U/L"),
    "AST": (10, 40, "U/L"),
    "TBIL": (3, 21, "umol/L"),
    "BUN": (2.9, 8.2, "mmol/L"),
    "FPG": (3.9, 6.1, "mmol/L"),
    "K+": (3.5, 5.5, "mmol/L"),
    "Troponin": (0, 0.04, "ng/mL"),
    "D-Dimer": (0, 0.5, "mg/L"),
    "PaO2": (80, 100, "mmHg"),
    "TSH": (0.4, 4.0, "mIU/L"),
}


def _load_vital_ranges() -> dict[str, tuple[float, float, str]]:
    """Load reference ranges from YAML config, fall back to defaults."""
    try:
        import yaml
        ranges_file = KNOWLEDGE_DIR / "rules" / "reference_ranges.yaml"
        if ranges_file.exists():
            with open(ranges_file, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            data = config.get("ranges", {})
            if data:
                return {
                    k: (v["low"], v["high"], v["unit"])
                    for k, v in data.items()
                }
    except Exception:
        logger.debug("Vital ranges load failed", exc_info=True)


_VITAL_RANGES = _load_vital_ranges()
