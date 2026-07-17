"""Tests for Sprint 1: Guard gating, T1/T2 enforcement, non-high-risk checks."""

import pytest

from haip.guard.verifier import GuardVerifier, GuardResult
from haip.guard.citation import CitationEngine, Citation


class TestGuardNonHighRisk:
    """S3-2: Non-high-risk scenarios should get citation-only lightweight check."""

    def test_non_high_risk_gets_citation_check(self):
        verifier = GuardVerifier()
        output = "患者目前状态稳定，建议继续口服药物。参考 NICE NG37 指南。"
        result = verifier.verify(agent_output=output, scenario="常规问诊", agent_name="test")
        # Non-high-risk still returns (not bypassed), citations are extracted
        assert isinstance(result.citations, list)
        # should still pass (no blocking for non-high-risk)
        assert result.passed is True

    def test_non_high_risk_empty_output(self):
        verifier = GuardVerifier()
        result = verifier.verify(agent_output="", scenario="", agent_name="test")
        assert result.passed is True

    def test_high_risk_triggers_full_pipeline(self):
        """Surgery keywords should trigger full 4-layer check."""
        verifier = GuardVerifier()
        output = (
            "建议进行全髋关节置换术 (THA)。术前评估显示患者 ASA II 级。"
            "手术方案: THA。术后预防 DVT 使用低分子肝素。"
        )
        result = verifier.verify(agent_output=output, scenario="手术决策", agent_name="orthopedic")
        # 高危场景 + 零引文 → 必须给出引文缺失提示
        assert any("引用" in f or "引文" in f for f in result.flags), result.flags
        assert isinstance(result.citations, list)


class TestT1T2Enforcement:
    """A3: T1/T2 trust enforcement."""

    def test_missing_t1_for_high_risk(self):
        """High-risk scenario with no T1 citations should be flagged."""
        verifier = GuardVerifier()
        output = (
            "手术方案: 建议行 PFNA 内固定。患者为高龄股骨转子间骨折。"
            "根据院内共识，应在 48 小时内手术。"
        )
        result = verifier.verify(agent_output=output, scenario="手术决策", agent_name="orthopedic")
        # 高危场景无 T1 引文 → 必须出现 T1/引文相关警示 (恒真断言已改实;
        # 原测试输出不含高危触发词, 前提失效被恒真断言掩盖, 已补 '手术方案' 触发词)
        has_t1_warning = any(
            "T1" in f or "引用" in f or "引文" in f for f in result.flags
        )
        assert has_t1_warning, result.flags

    def test_t1_keyword_detection(self):
        engine = CitationEngine()
        assert engine._guess_trust_level("根据 NICE NG37 指南") == "T1"
        assert engine._guess_trust_level("根据 WHO 标准") == "T1"
        assert engine._guess_trust_level("根据院内共识") == "T2"
        assert engine._guess_trust_level("专家建议") == "T2"

    def test_all_t1_static(self):
        citations = [
            Citation(trust_level="T1", source="NICE NG37"),
            Citation(trust_level="T1", source="AAOS 2022"),
        ]
        assert CitationEngine.all_t1(citations) is True

    def test_has_unverified(self):
        citations = [
            Citation(trust_level="T1", source="NICE NG37", verified=True),
            Citation(trust_level="T2", source="local", verified=False),
        ]
        assert CitationEngine.has_unverified(citations) is True

    def test_all_verified(self):
        citations = [
            Citation(trust_level="T1", source="AAOS", verified=True),
            Citation(trust_level="T1", source="NICE", verified=True),
        ]
        assert CitationEngine.has_unverified(citations) is False


class TestGuardResult:
    def test_default_passed(self):
        r = GuardResult()
        assert r.passed is True
        assert r.flags == []

    def test_blocked_flag(self):
        r = GuardResult(passed=False)
        r.flags.append("置信度不足")
        assert r.passed is False
        assert len(r.flags) == 1


class TestCitationExtraction:
    def test_extract_ref_tag(self):
        engine = CitationEngine()
        citations = engine.extract("建议手术 [ref: AAOS 2022 髋部骨折指南]")
        assert len(citations) >= 1

    def test_extract_cn_ref(self):
        engine = CitationEngine()
        citations = engine.extract("参考：NICE NG37 髋关节骨折管理指南。")
        assert len(citations) >= 1

    def test_format_summary(self):
        citations = [
            Citation(trust_level="T1", source="AAOS 2022", verified=True),
        ]
        summary = CitationEngine.format_summary(citations)
        assert "AAOS 2022" in summary
        assert "verified" in summary
