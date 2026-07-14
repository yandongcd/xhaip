"""Tests for Sprint 1: Citation enforcement + Version enforcement."""

import yaml

from haip.agent import CitationConfig, GuardConfig, DomainPlugin


YAML_WITH_CITATION = """
name: cardiology
cn_name: 心血管内科
type: business
port: 8700
prompt:
  system: 你是一个心血管内科AI助手
tools:
  - name: assess
    description: 评估心脏风险
    handler: cardiology.assess
guard:
  triggers: [药物交互]
  high_risk_scenarios: [围术期心肌梗死]
  citation:
    required: true
    min_sources: 2
    min_trust: T1
"""

YAML_WITHOUT_CITATION = """
name: dermatology
cn_name: 皮肤科
type: business
port: 8720
prompt:
  system: 你是一个皮肤科AI助手
tools:
  - name: assess
    description: 皮肤问题评估
    handler: dermatology.assess
guard:
  triggers: []
"""


class TestCitationConfig:
    def test_defaults(self):
        c = CitationConfig()
        assert c.required is False
        assert c.min_sources == 1
        assert c.min_trust == "T2"

    def test_custom(self):
        c = CitationConfig(required=True, min_sources=3, min_trust="T1")
        assert c.required is True
        assert c.min_sources == 3
        assert c.min_trust == "T1"


class TestGuardConfigWithCitation:
    def test_default_citation(self):
        g = GuardConfig(triggers=["测试"], high_risk_scenarios=["高危"])
        assert g.citation.required is False
        assert g.citation.min_sources == 1

    def test_explicit_citation(self):
        g = GuardConfig(
            triggers=["测试"],
            citation=CitationConfig(required=True, min_trust="T1"),
        )
        assert g.citation.required is True
        assert g.citation.min_trust == "T1"


class TestYamlLoaderCitation:
    def test_with_citation(self):
        data = yaml.safe_load(YAML_WITH_CITATION)
        plugin = DomainPlugin.from_yaml(data)
        assert plugin.guard.citation.required is True
        assert plugin.guard.citation.min_sources == 2
        assert plugin.guard.citation.min_trust == "T1"

    def test_without_citation_defaults(self):
        data = yaml.safe_load(YAML_WITHOUT_CITATION)
        plugin = DomainPlugin.from_yaml(data)
        assert plugin.guard.citation.required is False
        assert plugin.guard.citation.min_sources == 1
        assert plugin.guard.citation.min_trust == "T2"

    def test_citation_does_not_break_backward_compat(self):
        """Existing YAML without citation block must still load."""
        data = yaml.safe_load(YAML_WITHOUT_CITATION)
        plugin = DomainPlugin.from_yaml(data)
        assert plugin.name == "dermatology"
        assert plugin.guard.triggers == []
        assert plugin.guard.citation is not None


class TestVersionCheck:
    def test_exact_match(self):
        from haip.a2a import _check_version
        assert _check_version("1.0.0", "1.0.0") is True
        assert _check_version("1.0.0", "1.0.1") is False

    def test_gte_match(self):
        from haip.a2a import _check_version
        assert _check_version(">=1.0", "1.0.0") is True
        assert _check_version(">=1.0", "2.0.0") is True
        assert _check_version(">=1.0", "0.9.0") is False
        assert _check_version(">=1.5", "1.5.0") is True

    def test_equal_match(self):
        from haip.a2a import _check_version
        assert _check_version("==1.0", "1.0.0") is True
        assert _check_version("==1.0", "1.0.1") is False

    def test_invalid_version_graceful(self):
        from haip.a2a import _check_version
        assert _check_version(">=1.0", "invalid") is False
        assert _check_version("1.0.0", "") is False
