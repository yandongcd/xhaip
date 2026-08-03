"""Guard Verifier — 4层医疗安全验证管道."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from haip.guard.citation import Citation, CitationEngine
from haip.guard.confidence import ConfidenceScore, ConfidenceScorer
from haip.llm import DEFAULT_MAX_TOKENS, LLMProvider

logger = logging.getLogger(__name__)

# ── 高危场景触发条件 ──

HIGH_RISK_SCENARIOS = {
    "手术决策": ["手术时机", "术式推荐", "延迟手术", "手术方案", "THA", "HA", "PFNA", "surgery"],
    "药物交互": ["处方审核", "抗凝管理", "药物相互作用", "华法林", "低分子肝素", "anticoagulation"],
    "心梗评估": ["MI", "心梗", "cTnI", "肌钙蛋白", "STEMI", "NSTEMI", "ECG高危"],
    "麻醉评估": ["ASA III", "ASA IV", "困难气道", "麻醉方案"],
    "MDT分歧": ["结论不一致", "评估冲突", "分歧"],
}

# ── 交叉验证相反词对 ──

_CONFLICT_PAIRS = [
    ("高风险", "低风险"), ("高危", "安全"), ("延迟", "进行"),
    ("手术", "保守"), ("禁忌", "适用"), ("不推荐", "推荐"),
    ("停用", "继续"), ("不适宜", "适宜"), ("禁止", "允许"),
]


@dataclass
class GuardResult:
    passed: bool = True
    flags: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    confidence: ConfidenceScore | None = None
    corrected_output: str = ""
    requires_human_review: bool = False
    cross_validation_conflict: bool = False
    cross_validation_detail: str = ""
    # ── MED-2: 审问式安全 (Phase1) ──
    interrogated: bool = False
    interrogation: Any = None  # InterrogationReport (lazy import to avoid circular)


class GuardVerifier:
    """4层安全验证管道: 引文 → 置信度 → LLM 自纠 → 交叉验证."""

    def __init__(
        self,
        citation_engine: CitationEngine | None = None,
        confidence_scorer: ConfidenceScorer | None = None,
        llm_provider: LLMProvider | None = None,
        interrogation_enabled: bool = True,
    ):
        self.citation_engine = citation_engine or CitationEngine()
        self.confidence_scorer = confidence_scorer or ConfidenceScorer()
        self.llm = llm_provider
        self._interrogation_enabled = interrogation_enabled

    def verify(
        self,
        agent_output: str,
        scenario: str = "",
        agent_name: str = "",
        tool_results: list[dict] | None = None,
        cross_agent_outputs: list[str] | None = None,
        llm_temperature: float = 0.3,
        stage_score: int | None = None,
    ) -> GuardResult:
        try:
            return self._verify_impl(
                agent_output, scenario, agent_name,
                tool_results, cross_agent_outputs, llm_temperature,
                stage_score,
            )
        except Exception:
            logger.exception("Guard 验证管道内部异常, 阻断通过: agent=%s scenario=%s", agent_name, scenario)
            return GuardResult(passed=False, flags=["Guard 内部异常: 验证不可用"])

    def _verify_impl(
        self,
        agent_output: str,
        scenario: str = "",
        agent_name: str = "",
        tool_results: list[dict] | None = None,
        cross_agent_outputs: list[str] | None = None,
        llm_temperature: float = 0.3,
        stage_score: int | None = None,
    ) -> GuardResult:
        agent_output = agent_output.strip()
        result = GuardResult()

        # Stage audit gate — 医院流程质控评分门控 (score = 100 - failed*30 - critical*50 - warnings*10)
        #   <40 → 硬阻断 (存在 critical/failed 项)
        #   40-59 → 需人工复核
        if stage_score is not None:
            if stage_score < 40:
                result.passed = False
                result.flags.append(f"阶段审计不达标 (评分 {stage_score}/100) — 存在危急/不合格项，阻断通过")
            elif stage_score < 60:
                result.requires_human_review = True
                result.flags.append(f"阶段审计需优化 (评分 {stage_score}/100) — 建议人工复核")

        # Layer 1: Citation — always run (even for non-high-risk)
        citations = self.citation_engine.extract(agent_output)
        citations = self.citation_engine.verify(citations)
        result.citations = citations

        # Non-high-risk: citation-only lightweight check
        if not self._is_high_risk(scenario, agent_output):
            if self.citation_engine.has_unverified(citations):
                result.flags.append("存在未验证的指南引用 (低风险场景)")
            return result

        # ── High-risk: full 4-layer pipeline ──
        if self.citation_engine.has_unverified(citations):
            result.flags.append("存在未验证的指南引用")

        # T1/T2 trust enforcement for high-risk scenarios
        if not CitationEngine.all_t1(citations) and citations:
            result.flags.append("高危场景缺少 T1 级权威引用——建议升级引用源")
        if not citations:
            result.flags.append("高危场景无任何指南引用——建议补充引文")

        # Layer 2: Confidence
        score = self.confidence_scorer.compute(
            citations=citations,
            tool_results=tool_results or [],
            llm_temperature=llm_temperature,
        )
        result.confidence = score
        if score.blocked:
            result.passed = False
            result.flags.append(f"置信度不足 ({score.value:.2f})")
            return result
        if score.flagged_for_review:
            result.requires_human_review = True
            result.flags.append(f"需人工复核 (置信度 {score.value:.2f})")

        # Layer 3: LLM 自纠
        if self.llm:
            corrected = self._auto_correct(agent_output, agent_name)
            if corrected and len(corrected) > 20 and corrected != agent_output:
                result.corrected_output = corrected

        # ── Layer 3.5: MED-2 审问式安全审核 ──
        # 独立审问 agent 对输出做 9 维追问 (禁忌症/药物/剂量核心三维必过)
        if self._interrogation_enabled and self.llm:
            try:
                from haip.guard.interrogate import interrogate as run_interrogate
                report = run_interrogate(
                    agent_output=result.corrected_output or agent_output,
                    context=f"agent={agent_name} scenario={scenario}",
                    provider=self.llm,
                )
                result.interrogated = True
                result.interrogation = report
                if not report.is_clean():
                    result.flags.append(f"审问未通过 ({report.passed_dimensions}/9, 核心{report.core_passed}/3)")
                    if report.requires_human_review:
                        result.requires_human_review = True
                else:
                    result.flags.append(f"审问通过 ({report.passed_dimensions}/9)")
            except Exception:
                logger.debug("审问式 Guard 执行异常", exc_info=True)

        # Layer 4: Cross-validation
        if cross_agent_outputs:
            conflicts = self._detect_conflicts(agent_output, cross_agent_outputs)
            if conflicts:
                result.cross_validation_conflict = True
                result.cross_validation_detail = "; ".join(conflicts)
                result.flags.append("跨Agent结论存在冲突")

        result.passed = result.passed and not result.cross_validation_conflict
        return result

    @staticmethod
    def _is_high_risk(scenario: str, text: str) -> bool:
        combined = f"{scenario} {text}".lower()
        for keywords in HIGH_RISK_SCENARIOS.values():
            if any(kw.lower() in combined for kw in keywords):
                return True
        return False

    def _auto_correct(self, output: str, agent_name: str) -> str:
        if self.llm is None:
            return ""
        try:
            resp = self.llm.chat(
                messages=[
                    {"role": "system", "content": (
                        "你是医疗审核专家。审查以下输出，纠正事实错误，补充遗漏的安全警示。"
                        "只输出修正后的内容，不要做其他解释。"
                    )},
                    {"role": "user", "content": f"Agent [{agent_name}] 输出:\n{output}"},
                ],
                temperature=0.05,
                max_tokens=DEFAULT_MAX_TOKENS,
            )
            return resp.content.strip()
        except Exception:
            logger.warning("LLM 审查失败, agent=%s", agent_name, exc_info=True)
            return ""

    @staticmethod
    def _detect_conflicts(main: str, others: list[str]) -> list[str]:
        conflicts: list[str] = []
        main_lower = main.lower()
        for other in others:
            other_lower = other.lower()
            for high, low in _CONFLICT_PAIRS:
                has_high_main = high in main_lower
                has_low_other = low in other_lower
                has_low_main = low in main_lower
                has_high_other = high in other_lower
                if (has_high_main and has_low_other) or (has_low_main and has_high_other):
                    conflicts.append(f"{high}/{low}")
                    break
        return conflicts[:3]

    def bind_llm(self, llm: LLMProvider) -> None:
        self.llm = llm
