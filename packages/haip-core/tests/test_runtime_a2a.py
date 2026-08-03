"""Tests for Stage 9: Runtime A2A Validation."""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from haip.meta_harness import MetaHarness


class TestRuntimeA2A:
    """Test Stage 9 runtime A2A validation."""

    def test_stage_exists(self):
        mh = MetaHarness()
        assert hasattr(mh, "_run_runtime_a2a")
        assert callable(mh._run_runtime_a2a)

    def test_build_runtime_params_basic(self):
        mh = MetaHarness()
        patient = {"patient_id": "P001", "age": 65, "weight_kg": 70, "lab_results": {"hb": 12.5}}
        tool = {"input": {"age": "int", "weight_kg": "float", "hb": "float"}}
        params = mh._build_runtime_params(patient, tool)
        assert params["patient_id"] == "P001"
        assert params["age"] == 65
        assert params["weight_kg"] == 70
        assert params["hb"] == 12.5

    def test_build_runtime_params_from_lab_results(self):
        mh = MetaHarness()
        patient = {"patient_id": "P001", "lab_results": {"crp": 107.3, "albumin": 35.5}}
        tool = {"input": {"crp": "float", "albumin": "float"}}
        params = mh._build_runtime_params(patient, tool)
        assert params["crp"] == 107.3
        assert params["albumin"] == 35.5

    def test_build_runtime_params_missing_keys(self):
        mh = MetaHarness()
        patient = {"patient_id": "P001"}
        tool = {"input": {"name": "str", "age": "int"}}
        params = mh._build_runtime_params(patient, tool)
        assert params["patient_id"] == "P001"
        assert "name" not in params
        assert "age" not in params

    def test_validate_runtime_response_pass(self):
        mh = MetaHarness()
        resp = {"status": "ok", "result": {"score": 85}}
        result = mh._validate_runtime_response(resp, "test_tool", "test_agent", {"patient_id": "P001"}, 12.5)
        assert result["status"] == "pass"
        assert result["agent"] == "test_agent"
        assert result["elapsed_ms"] == 12.5
        assert "score" in result.get("response_summary", "")

    def test_validate_runtime_response_error(self):
        mh = MetaHarness()
        resp = {"status": "error", "error": "handler not found"}
        result = mh._validate_runtime_response(resp, "test_tool", "test_agent", {"patient_id": "P001"}, 5.0)
        assert result["status"] == "fail"
        assert result["error_type"] == "a2a_error"

    def test_validate_runtime_response_blocked(self):
        mh = MetaHarness()
        resp = {"status": "blocked", "error": "guard triggered"}
        result = mh._validate_runtime_response(resp, "test_tool", "test_agent", {"patient_id": "P001"}, 8.0)
        assert result["status"] == "blocked"
        assert result["error_type"] == "guard_blocked"

    def test_validate_runtime_response_empty(self):
        mh = MetaHarness()
        resp = {"status": "ok", "result": {}}
        result = mh._validate_runtime_response(resp, "test_tool", "test_agent", {"patient_id": "P001"}, 3.0)
        assert result["status"] == "fail"
        assert result["error_type"] == "empty_result"

    def test_validate_runtime_response_invalid_type(self):
        mh = MetaHarness()
        result = mh._validate_runtime_response("not_a_dict", "test_tool", "test_agent", {"patient_id": "P001"}, 1.0)
        assert result["status"] == "fail"
        assert result["error_type"] == "invalid_response_type"

    def test_get_runtime_patients(self):
        mh = MetaHarness()
        patients = mh._get_runtime_patients("pharmacy")
        assert isinstance(patients, list)
        if patients:
            p0 = patients[0]
            assert "patient_id" in p0

    def test_run_runtime_a2a_structure(self):
        mh = MetaHarness()
        result = mh._run_runtime_a2a()
        assert "status" in result
        assert "total" in result
        assert "passed" in result
        assert "failed" in result
        assert "score" in result
        assert "timing" in result
        assert "failures" in result
        assert "by_agent" in result
        assert result["status"] == "completed"

    def test_run_runtime_a2a_by_agent(self):
        mh = MetaHarness()
        result = mh._run_runtime_a2a()
        by_agent = result.get("by_agent", {})
        assert isinstance(by_agent, dict)
        if by_agent:
            first = next(iter(by_agent.values()))
            assert "total" in first
            assert "passed" in first
            assert "failed" in first

    def test_full_cycle_includes_runtime_a2a(self):
        mh = MetaHarness()
        report = mh.run_full_cycle(run_proposer=False)
        stages = report.get("stages", {})
        assert "runtime_a2a" in stages
        assert stages["runtime_a2a"]["status"] == "completed"

    def test_full_cycle_score_includes_runtime(self):
        mh = MetaHarness()
        report = mh.run_full_cycle(run_proposer=False)
        assert report["unified_score"] >= 0
