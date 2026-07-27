"""Guard 异常场景: fail-closed 验证 — Guard 内部异常必须阻断通过."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from haip.guard import GuardResult, GuardVerifier
from haip.guard.citation import Citation


class TestGuardFailClosed:
    def test_citation_extract_exception_returns_error(self):
        """Citation 引擎 extract() 异常时, verify 应返回 error 而非 crash"""
        verifier = GuardVerifier()
        with patch.object(
            verifier.citation_engine, "extract",
            side_effect=RuntimeError("citation extract crash"),
        ):
            result = verifier.verify(
                agent_output="建议进行乳腺超声检查。",
                scenario="高危场景",
                agent_name="breast-center",
            )
            assert not result.passed

    def test_citation_verify_exception_returns_error(self):
        """Citation 引擎 verify() 异常时返回 error"""
        verifier = GuardVerifier()
        with patch.object(
            verifier.citation_engine, "verify",
            side_effect=RuntimeError("citation verify crash"),
        ):
            result = verifier.verify(
                agent_output="建议进行乳腺超声检查。",
                scenario="手术时机评估",
                agent_name="breast-center",
            )
            assert not result.passed

    def test_confidence_compute_exception_returns_error(self):
        """Confidence 评分异常时, verify 应返回 error（高危场景触发全管线）"""
        verifier = GuardVerifier()
        mock_citation = Citation(
            source="NCCN 2023 指南",
            trust_level="T1",
            verified=True,
        )
        with patch.object(
            verifier.citation_engine, "extract",
            return_value=[mock_citation],
        ):
            with patch.object(
                verifier.citation_engine, "verify",
                return_value=[mock_citation],
            ):
                with patch.object(
                    verifier.confidence_scorer, "compute",
                    side_effect=ValueError("confidence crash"),
                ):
                    result = verifier.verify(
                        agent_output="建议进行 THA 手术方案评估。",
                        scenario="手术时机评估",
                        agent_name="orthopedic-surgery",
                    )
                    assert not result.passed

    def test_auto_correct_exception_still_verifies(self):
        """LLM 自纠异常不应影响整体验证结果（自纠仅增强，非安全门控）"""
        verifier = GuardVerifier()
        mock_citation = Citation(
            source="NCCN 2023 乳腺癌指南",
            trust_level="T1",
            verified=True,
        )
        with patch.object(
            verifier.citation_engine, "extract",
            return_value=[mock_citation],
        ):
            with patch.object(
                verifier.citation_engine, "verify",
                return_value=[mock_citation],
            ):
                with patch.object(
                    verifier, "_auto_correct",
                    side_effect=RuntimeError("LLM crash in auto-correct"),
                ):
                    result = verifier.verify(
                        agent_output="根据 NCCN 2023 指南，建议进行 THA 手术。",
                        scenario="手术方案决策",
                        agent_name="orthopedic-surgery",
                    )
                    assert result.citations

    def test_empty_content_handled(self):
        """空内容应返回合法 GuardResult"""
        verifier = GuardVerifier()
        result = verifier.verify(
            agent_output="",
            scenario="",
            agent_name="test_agent",
        )
        assert isinstance(result, GuardResult)

    def test_normal_pipeline_still_works(self):
        """正常验证流程不应受 fail-closed 改造影响"""
        verifier = GuardVerifier()
        mock_citation = Citation(
            source="NCCN 2023 乳腺癌指南",
            trust_level="T1",
            verified=True,
        )
        with patch.object(
            verifier.citation_engine, "extract",
            return_value=[mock_citation],
        ):
            with patch.object(
                verifier.citation_engine, "verify",
                return_value=[mock_citation],
            ):
                result = verifier.verify(
                    agent_output="根据 NCCN 2023 指南，建议进行乳腺超声检查。",
                    scenario="乳腺筛查",
                    agent_name="breast-center",
                )
                assert isinstance(result, GuardResult)
                assert result.citations
