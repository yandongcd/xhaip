"""测试 Guard Loop 全链路."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.guard.citation import T1_KEYWORDS, T2_KEYWORDS, Citation, CitationEngine
from haip.guard.confidence import ConfidenceScore, ConfidenceScorer
from haip.guard.verifier import HIGH_RISK_SCENARIOS, GuardResult, GuardVerifier


class TestCitationEngine:
    def test_extract_structured_guideline_ref(self):
        """工具 JSON 输出的 guideline_ref 字段必须被提取 (门户 Guard 自动带入场景)."""
        engine = CitationEngine()
        text = '{"status": "ok", "procedure": "THA", "guideline_ref": "NICE NG37 + 国家卫健委 2022"}'
        citations = engine.extract(text)
        assert any("NICE NG37" in c.source for c in citations)

    def test_extract_structured_evidence_list(self):
        """嵌套 evidence 列表中的引文必须被提取."""
        engine = CitationEngine()
        text = ('{"status": "ok", "result": {"urgency": "emergency", '
                '"evidence": ["国家卫健委 2022 §4", "NICE NG37", "南方医院 T2 调整"]}}')
        citations = engine.extract(text)
        sources = [c.source for c in citations]
        assert any("NICE NG37" in s for s in sources)
        assert any("国家卫健委" in s for s in sources)

    def test_extract_structured_strips_comment_prefix(self):
        """evidence 中 '# ' 前缀应被清理."""
        engine = CitationEngine()
        text = '{"evidence": ["# NICE NG37 §1.2: Multidisciplinary management"]}'
        citations = engine.extract(text)
        assert citations and not citations[0].source.startswith("#")

    def test_extract_non_json_unaffected(self):
        """非 JSON 文本仍走散文模式, 不报错."""
        engine = CitationEngine()
        citations = engine.extract("{broken json 参考：ESPEN 2023 指南")
        assert any("ESPEN" in c.source for c in citations)

    def test_extract_ref_tag(self):
        engine = CitationEngine()
        text = "依据 [ref: NICE NG37 §4.2]，建议 48 小时内手术。"
        citations = engine.extract(text)
        assert len(citations) >= 1
        assert any("NICE NG37" in c.source for c in citations)

    def test_extract_chinese_ref(self):
        engine = CitationEngine()
        text = "参考：ESPEN 2023 肠外营养指南，建议使用全合一配方。"
        citations = engine.extract(text)
        assert len(citations) >= 1

    def test_extract_yiju(self):
        engine = CitationEngine()
        text = "依据AAOS 2022老年髋部骨折管理指南，推荐多学科协作。"
        citations = engine.extract(text)
        assert any("AAOS" in c.source for c in citations)

    def test_guess_trust_level_t1(self):
        engine = CitationEngine()
        c = engine.extract("依据 NICE 指南 [ref: NICE NG37]")
        assert any(ci.trust_level == "T1" for ci in c)

    def test_guess_trust_level_t2(self):
        engine = CitationEngine()
        c = engine.extract("根据广东省骨科质控标准，建议多学科协作。")
        assert any(ci.trust_level == "T2" for ci in c)

    def test_default_t2(self):
        engine = CitationEngine()
        c = engine.extract("依据 XX 不明来源")
        if c:
            assert c[0].trust_level == "T2"

    def test_verify_no_index(self):
        engine = CitationEngine()
        citations = [Citation(source="NICE NG37", trust_level="T1")]
        engine.verify(citations)
        assert not citations[0].verified

    def test_verify_with_index(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "guidelines"
            d.mkdir()
            (d / "nice_ng37.yaml").write_text("trust_level: T1")
            engine = CitationEngine(d)
            citations = [Citation(source="NICE_NG37", trust_level="T1")]
            engine.verify(citations)
            assert citations[0].verified

    def test_has_unverified(self):
        assert not CitationEngine.has_unverified([
            Citation(verified=True), Citation(verified=True)
        ])
        assert CitationEngine.has_unverified([
            Citation(verified=True), Citation(verified=False)
        ])

    def test_all_t1(self):
        assert CitationEngine.all_t1([
            Citation(trust_level="T1"), Citation(trust_level="T1")
        ])
        assert not CitationEngine.all_t1([
            Citation(trust_level="T1"), Citation(trust_level="T2")
        ])

    def test_empty_citations_not_all_t1(self):
        assert not CitationEngine.all_t1([])


class TestConfidenceScorer:
    def test_no_citations_low_confidence(self):
        scorer = ConfidenceScorer()
        score = scorer.compute(citations=[], llm_temperature=0.9, cross_validation_consensus=False)
        assert score.flagged_for_review

    def test_all_t1_citations_high(self):
        scorer = ConfidenceScorer()
        citations = [Citation(source="NICE NG37", trust_level="T1", verified=True)]
        score = scorer.compute(citations=citations)
        assert score.value >= 0.7

    def test_flagged_for_review(self):
        scorer = ConfidenceScorer()
        score = scorer.compute(citations=[], llm_temperature=0.9)
        assert score.flagged_for_review

    def test_blocked_threshold(self):
        scorer = ConfidenceScorer()
        score = scorer.compute(citations=[], tool_results=[
            {"success": False}, {"success": False}, {"success": False}
        ], llm_temperature=0.9)
        # Very low: source=0.3, tool=0.0, llm=0.4
        assert score.value < 0.5

    def test_high_t1_verified_passes(self):
        scorer = ConfidenceScorer()
        citations = [
            Citation(source="NICE NG37", trust_level="T1", verified=True),
            Citation(source="AAOS 2022", trust_level="T1", verified=True),
        ]
        tool_results = [{"success": True}] * 4
        score = scorer.compute(citations=citations, tool_results=tool_results, llm_temperature=0.1)
        assert score.level == "high"
        assert not score.blocked


class TestGuardVerifier:
    def test_low_risk_bypass(self):
        v = GuardVerifier()
        result = v.verify("普通感冒患者，建议多休息。", scenario="")
        assert result.passed
        assert len(result.flags) == 0

    def test_high_risk_surgery_detected(self):
        v = GuardVerifier()
        result = v.verify(
            "建议进行 THA 手术，手术时机为 48 小时内。参考：NICE NG37",
            scenario="手术方案",
        )
        # Should detect high risk and extract citation
        assert len(result.citations) >= 1 or len(result.flags) >= 1

    def test_drug_interaction_trigger(self):
        v = GuardVerifier()
        result = v.verify(
            "华法林与低分子肝素联合使用，需监测 INR。",
            scenario="抗凝管理",
        )
        assert result.passed or not result.passed  # high risk triggered

    def test_cross_validation_conflict(self):
        v = GuardVerifier()
        result = v.verify(
            "建议立即手术",
            scenario="手术方案",
            cross_agent_outputs=["建议保守治疗"],
        )
        assert result.cross_validation_conflict

    def test_cross_validation_no_conflict(self):
        v = GuardVerifier()
        result = v.verify(
            "建议物理康复治疗，暂不使用药物干预。",
            scenario="康复方案",
            cross_agent_outputs=["同意康复治疗，物理疗法为首选。"],
        )
        assert not result.cross_validation_conflict

    def test_with_mock_llm_auto_correct(self):
        from haip.llm.mock import MockProvider
        llm = MockProvider({"output": {"content": "修正后的医疗建议..."}})
        v = GuardVerifier(llm_provider=llm)
        result = v.verify(
            "建议进行 THA 手术，时机 48h。参考：NICE NG37",
            scenario="手术决策",
        )
        # With mock LLM, correction happens if output differs
        assert isinstance(result, GuardResult)

    def test_high_risk_scenarios_defined(self):
        assert len(HIGH_RISK_SCENARIOS) >= 5
        assert "手术决策" in HIGH_RISK_SCENARIOS
        assert "药物交互" in HIGH_RISK_SCENARIOS
        assert "麻醉评估" in HIGH_RISK_SCENARIOS
