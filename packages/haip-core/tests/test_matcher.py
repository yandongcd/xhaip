"""Smoke tests for agent name matcher."""
import pytest

from haip.agent.matcher import _normalize, get_display_name, resolve, search


class TestMatcher:
    def test_resolve_exact_alias(self):
        assert resolve("药剂科") == "pharmacy"
        assert resolve("骨科") == "orthopedic-surgery"
        assert resolve("心外科") == "cardio-surgery"

    def test_resolve_canonical(self):
        assert resolve("pharmacy") == "pharmacy"
        assert resolve("cardio-risk") == "cardio-risk"

    def test_resolve_substring(self):
        assert resolve("心脏") == "cardio-surgery"  # "心外科" alias matches first

    def test_resolve_empty(self):
        assert resolve("") is None
        assert resolve("   ") is None

    def test_resolve_unknown(self):
        assert resolve("不存在的智能体xyz") is None

    def test_normalize(self):
        assert _normalize("骨科 agent") == "骨科"
        assert _normalize("心脏评估智能体") == "心脏评估"

    def test_search(self):
        results = search("骨")
        assert len(results) > 0
        assert results[0]["name"] == "orthopedic-surgery"

    def test_search_empty(self):
        assert search("") == []

    def test_get_display_name(self):
        name = get_display_name("orthopedic-surgery")
        assert isinstance(name, str)
        assert len(name) > 0
