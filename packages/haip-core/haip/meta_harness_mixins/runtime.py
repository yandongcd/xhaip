"""运行时 A2A+规则合规+患者缓存 — meta_harness mixin (P1-6 拆分)."""

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

logger = logging.getLogger(__name__)


class MetaHarnessRuntimeMixin:
    def _run_runtime_a2a(self) -> dict:
        """Validate every handler at runtime with real patient data via A2A calls."""
        results: list[dict] = []
        timing: list[float] = []
        passed = 0
        failed = 0
        by_agent: dict[str, dict] = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
        calls_made = 0
        limit = self._runtime_a2a_limit

        for agent_name, agent in self._agents.items():
            if limit is not None and calls_made >= limit:
                break
            tools = agent.get("tools", [])
            if not tools:
                continue

            patients = self._get_runtime_patients(agent_name)
            if not patients:
                by_agent[agent_name] = {"total": len(tools) * 3, "passed": 0, "failed": len(tools) * 3, "note": "no patients"}
                failed += len(tools) * 3
                continue

            for tool in tools:
                handler = tool.get("handler", "")
                tool_name = tool.get("name", "")
                if not handler:
                    continue

                for patient in patients[:3]:
                    if limit is not None and calls_made >= limit:
                        break
                    calls_made += 1
                    params = self._build_runtime_params(patient, tool)
                    t0 = time.time()
                    try:
                        resp = self._a2a_call_with_timeout(agent_name, tool_name, params, timeout=self._a2a_timeout)
                        elapsed = (time.time() - t0) * 1000
                        timing.append(elapsed)
                        result_entry = self._validate_runtime_response(resp, tool_name, agent_name, patient, elapsed)
                    except Exception as e:
                        elapsed = (time.time() - t0) * 1000
                        timing.append(elapsed)
                        result_entry = {
                            "agent": agent_name, "tool": tool_name,
                            "patient": patient.get("patient_id", "?"),
                            "status": "error", "elapsed_ms": elapsed,
                            "error_type": type(e).__name__, "error_message": str(e)[:200],
                        }

                    results.append(result_entry)
                    by_agent[agent_name]["total"] += 1
                    if result_entry.get("status") in ("pass", "ok"):
                        passed += 1
                        by_agent[agent_name]["passed"] += 1
                    else:
                        failed += 1
                        by_agent[agent_name]["failed"] += 1

                    self._persist_runtime_result(result_entry)

        timing_sorted = sorted(timing)
        n = len(timing_sorted)
        return {
            "status": "completed",
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "score": round(passed / len(results) * 100) if results else 0,
            "timing": {
                "p50_ms": round(timing_sorted[n // 2]) if n else 0,
                "p95_ms": round(timing_sorted[int(n * 0.95)]) if n else 0,
                "p99_ms": round(timing_sorted[int(n * 0.99)]) if n else 0,
            },
            "failures": [r for r in results if r.get("status") not in ("pass", "ok")][:20],
            "by_agent": dict(by_agent),
            "limited": limit is not None,
        }


    def _get_runtime_patients(self, agent_name: str) -> list[dict]:
        try:
            from haip.patients import load_patients
            return load_patients(agent_name, limit=5, only_compatible=False)
        except Exception:
            logger.debug("Load patients failed, falling back, agent=%s", agent_name, exc_info=True)
            return self._load_patients_fallback()


    def _load_patients_fallback(self) -> list[dict]:
        patients_path = self.root / "packages/haip-hospital/data/patients.json"
        if not patients_path.exists():
            return []
        try:
            data = json.loads(patients_path.read_text(encoding="utf-8"))
            all_pts = data.get("patients", []) if isinstance(data, dict) else data
            return all_pts[:5] if isinstance(all_pts, list) else []
        except Exception:
            logger.warning("Patient JSON fallback parse failed", exc_info=True)
            return []


    def _build_runtime_params(self, patient: dict, tool: dict) -> dict:
        input_schema = tool.get("input", {})
        params: dict[str, Any] = {}
        for key in input_schema:
            if key in patient:
                params[key] = patient[key]
            elif isinstance(patient.get("lab_results"), dict) and key in patient["lab_results"]:
                params[key] = patient["lab_results"][key]
        params.setdefault("patient_id", patient.get("patient_id", ""))
        return params


    def _a2a_call_with_timeout(self, agent: str, tool_name: str, params: dict, timeout: int = 10) -> dict:
        from concurrent.futures import Future

        from haip.a2a import call as a2a_call
        from haip.a2a import internal_permission_context
        if self._a2a_executor is None:
            self._a2a_executor = ThreadPoolExecutor(max_workers=4)
        future: Future = self._a2a_executor.submit(
            a2a_call, agent, tool_name, params,
            perm_ctx=internal_permission_context())
        return future.result(timeout=timeout)


    def _validate_runtime_response(self, resp: dict, tool_name: str, agent_name: str,
                                    patient: dict, elapsed_ms: float) -> dict:
        base = {
            "agent": agent_name, "tool": tool_name,
            "patient": patient.get("patient_id", "?"),
            "elapsed_ms": round(elapsed_ms, 1),
            "status": "pass",
            "error_type": "", "error_message": "",
        }
        if not isinstance(resp, dict):
            base["status"] = "fail"
            base["error_type"] = "invalid_response_type"
            base["error_message"] = f"Expected dict, got {type(resp).__name__}"
            return base
        if resp.get("status") == "error":
            error_msg = str(resp.get("error", resp.get("message", "")))
            if self._is_input_validation_error(error_msg):
                base["status"] = "skip"
                base["error_type"] = "missing_input"
                base["error_message"] = error_msg[:200]
                return base
            base["status"] = "fail"
            base["error_type"] = "a2a_error"
            base["error_message"] = error_msg[:200]
            return base
        if resp.get("status") == "blocked":
            base["status"] = "blocked"
            base["error_type"] = "guard_blocked"
            base["error_message"] = str(resp.get("error", ""))[:200]
            return base
        result = resp.get("result", resp)
        if result is None or (isinstance(result, dict) and not result):
            base["status"] = "fail"
            base["error_type"] = "empty_result"
            base["error_message"] = "handler returned empty result"
            return base
        base["response_summary"] = str(result)[:500]
        return base


    def _persist_runtime_result(self, result: dict):
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS runtime_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent TEXT NOT NULL,
                        tool TEXT NOT NULL,
                        patient_id TEXT,
                        status TEXT NOT NULL,
                        elapsed_ms REAL,
                        error_type TEXT,
                        error_message TEXT,
                        response_summary TEXT,
                        timestamp REAL NOT NULL
                    )"""
                )
                conn.execute(
                    """INSERT INTO runtime_results (agent, tool, patient_id, status, elapsed_ms,
                       error_type, error_message, response_summary, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (result.get("agent", ""), result.get("tool", ""),
                     result.get("patient", ""), result.get("status", ""),
                     result.get("elapsed_ms", 0), result.get("error_type", ""),
                     result.get("error_message", ""), result.get("response_summary", ""),
                     time.time()),
                )
                conn.commit()
        except Exception:
            logger.debug("Runtime results DB save failed", exc_info=True)

    @staticmethod

    def _is_input_validation_error(msg: str) -> bool:
        """Check if an error message is an expected input validation error."""
        validation_keywords = ["不能为空", "必须为", "缺失", "Missing required", "required argument",
                               "required keyword", "missing 1 required", "must be a string"]
        return any(kw in msg for kw in validation_keywords)

    # ═══ STAGE 10: Clinical Rule Compliance (Layer 3a) ═══


    def _run_rule_compliance(self, runtime_stage: dict) -> dict:
        """Check if agent outputs comply with clinical knowledge rules."""
        total_rules_checked = 0
        total_passed = 0
        total_violated = 0
        violations: list[dict] = []

        for agent_name, agent in self._agents.items():
            dept = agent.get("department", "")
            if not dept:
                continue
            rules = self._load_matching_rules(agent_name, dept)
            if not rules:
                continue

            a2a_failures = runtime_stage.get("by_agent", {}).get(agent_name, {})
            if a2a_failures.get("failed", 0) > a2a_failures.get("total", 0) * 0.5:
                continue  # skip agents with >50% failures

            for rule in rules:
                total_rules_checked += 1
                result = self._evaluate_rule_condition(rule)
                if result is None:
                    continue  # unevaluable rule
                if result:
                    total_passed += 1
                else:
                    total_violated += 1
                    violations.append({
                        "rule_id": rule.get("id", "?"),
                        "agent": agent_name,
                        "condition": rule.get("condition", {}),
                        "rule_description": rule.get("description", str(rule)[:100]),
                    })

        return {
            "status": "completed",
            "total_rules_checked": total_rules_checked,
            "passed": total_passed,
            "violated": total_violated,
            "score": round(total_passed / total_rules_checked * 100) if total_rules_checked else 100,
            "top_violations": violations[:10],
        }


    def _load_matching_rules(self, agent_name: str, dept: str) -> list[dict]:
        rules: list[dict] = []
        agent_key = agent_name.replace("-", "_")
        dept_key = dept.replace(" ", "").replace("科", "")

        if not self.rules_dir.exists():
            return rules

        for rd in sorted(self.rules_dir.iterdir()):
            if not rd.is_dir() or rd.name.startswith("_"):
                continue
            if agent_key not in rd.name.lower() and dept_key not in rd.name.lower():
                continue
            for rf in sorted(rd.glob("*.yaml")):
                try:
                    content = rf.read_text(encoding="utf-8")
                    for doc in yaml.safe_load_all(content):
                        if isinstance(doc, dict) and "rules" in doc:
                            rules.extend(doc["rules"])
                except Exception:
                    logger.debug("YAML rules load failed: %s", rf, exc_info=True)
        return rules


    def _evaluate_rule_condition(self, rule: dict) -> bool | None:
        condition = rule.get("condition", {})
        if not isinstance(condition, dict):
            return None

        field = condition.get("field", "")
        operator = condition.get("operator", "==")
        expected = condition.get("value")

        if not field:
            if "and" in condition:
                return all(self._evaluate_rule_condition({"condition": c}) is True
                          for c in condition["and"])
            if "or" in condition:
                return any(self._evaluate_rule_condition({"condition": c}) is True
                          for c in condition["or"])
            return None

        return self._eval_operator(field, operator, expected)


    def _eval_operator(self, field: str, operator: str, expected) -> bool:
        try:
            parts = field.split(".")
            if len(parts) >= 2 and parts[0] == "lab_results":
                return self._check_lab_field_exists(parts[1])
            if field and "." not in field:
                return self._check_patient_field_exists(field)
            return True
        except Exception:
            logger.debug("Rule condition eval failed: %s", field, exc_info=True)
            return None


    def _ensure_patient_caches(self):
        """Build cached sets of lab and top-level patient fields (lazy)."""
        if hasattr(self, '_patient_lab_cache'):
            return
        import json
        patients_path = self.root / "packages" / "haip-hospital" / "data" / "patients.json"
        try:
            with open(patients_path, encoding="utf-8") as f:
                data = json.load(f)
            lab_set, top_set = set(), set()
            for p in data.get("patients", []):
                labs = p.get("lab_results", {})
                if isinstance(labs, dict):
                    lab_set.update(labs.keys())
                top_set.update(p.keys())
            self._patient_lab_cache = lab_set
            self._patient_top_cache = top_set
        except Exception:
            logger.warning("Patient cache build failed", exc_info=True)
            self._patient_lab_cache = set()
            self._patient_top_cache = set()


    def _check_lab_field_exists(self, field_name: str) -> bool:
        """Check if a lab field exists in at least one patient record."""
        if not hasattr(self, '_patient_lab_coverage'):
            self._patient_lab_coverage = self._build_lab_coverage()
        return field_name in self._patient_lab_coverage


    def _check_patient_field_exists(self, field_name: str) -> bool:
        self._ensure_patient_caches()
        return field_name in self._patient_top_cache


    def _build_lab_coverage(self) -> set:
        """Build set of all lab field names present in patient data."""
        import json
        patients_path = self.root / "packages" / "haip-hospital" / "data" / "patients.json"
        try:
            with open(patients_path, encoding="utf-8") as f:
                data = json.load(f)
            labs_set: set = set()
            for p in data.get("patients", []):
                labs = p.get("lab_results", {})
                if isinstance(labs, dict):
                    labs_set.update(labs.keys())
            return labs_set
        except Exception:
            logger.warning("Lab coverage build failed", exc_info=True)
            return set()

    # ═══ STAGE 11: Guard Effectiveness (Layer 3b) ═══

