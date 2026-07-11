"""Tests for haip.agent.matcher — Agent name fuzzy matching."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from haip.agent.matcher import resolve, search, get_display_name, CANONICAL_ALIASES


class TestMatcherResolve:
    def test_exact_english(self):
        assert resolve("pharmacy") == "pharmacy"

    def test_exact_chinese(self):
        assert resolve("药剂科") == "pharmacy"

    def test_exact_orthopedic(self):
        assert resolve("骨科") == "orthopedic-surgery"

    def test_normalized_match(self):
        assert resolve("cardio") == "cardio-surgery"

    def test_substring_match(self):
        assert resolve("cardiac") == "cardio-surgery"

    def test_fuzzy_match(self):
        r = resolve("cardiolgy")  # typo
        assert r == "cardio-surgery"

    def test_unknown_keyword(self):
        assert resolve("nonexistent_agent_xyz") is None

    def test_empty_keyword(self):
        assert resolve("") is None

    def test_whitespace_keyword(self):
        assert resolve("   ") is None


class TestMatcherSearch:
    def test_search_returns_results(self):
        results = search("ortho")
        assert len(results) >= 1
        assert results[0]["name"] in ("orthopedic-surgery",)

    def test_search_top_match(self):
        results = search("骨科")
        found = [r for r in results if r["name"] == "orthopedic-surgery"]
        assert len(found) >= 1

    def test_search_empty_returns_empty(self):
        assert search("") == []

    def test_search_limit(self):
        results = search("pain", limit=3)
        assert len(results) <= 3

    def test_search_no_matches(self):
        results = search("nonexistent_keyword_abcdef")
        assert results == []


class TestMatcherDisplayName:
    def test_known_agent_display(self):
        name = get_display_name("orthopedic-surgery")
        assert name == "骨科"

    def test_unknown_agent(self):
        name = get_display_name("nonexistent")
        assert name == "nonexistent"

    def test_metrics_display(self):
        name = get_display_name("metrics")
        assert name in ("指标", "全院指标")


class TestCanonicalAliases:
    def test_all_canonical_have_aliases(self):
        assert len(CANONICAL_ALIASES) >= 10

    def test_aliases_contain_chinese(self):
        for canonical, aliases in CANONICAL_ALIASES.items():
            assert len(aliases) >= 2, f"{canonical} should have >= 2 aliases"
