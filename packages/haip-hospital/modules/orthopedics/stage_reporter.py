"""Stage Audit Report — 11-Stage 审计评分与留痕.

借鉴药剂科 PrescriptionReview 的评分模型:
  score = 100 - failed×30 - critical×50 - warnings×10
  结论: 完全达标 / 需优化 / 不达标
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class StageAuditItem:
    category: str
    status: str           # passed / warning / failed / critical
    detail: str
    suggestion: str = ""
    guideline_ref: str = ""
    evidence: str = ""


@dataclass
class StageAuditReport:
    stage_id: str
    stage_name: str
    role: str
    timestamp: datetime = field(default_factory=datetime.now)
    items: list[StageAuditItem] = field(default_factory=list)
    score: int = 100
    conclusion: str = "未评估"
    appeal: str = ""
    reviewer: str = ""

    def add_item(self, category: str, status: str, detail: str,
                 suggestion: str = "", guideline_ref: str = "",
                 evidence: str = "") -> None:
        self.items.append(StageAuditItem(
            category=category, status=status, detail=detail,
            suggestion=suggestion, guideline_ref=guideline_ref,
            evidence=evidence,
        ))

    def finalize(self) -> None:
        failed = sum(1 for i in self.items if i.status == "failed")
        warnings = sum(1 for i in self.items if i.status == "warning")
        criticals = sum(1 for i in self.items if i.status == "critical")
        self.score = max(0, 100 - failed * 30 - criticals * 50 - warnings * 10)

        if criticals > 0:
            self.conclusion = f"不达标（{criticals}项危急）"
        elif failed > 0:
            self.conclusion = f"不达标（{failed}项不合格）"
        elif warnings > 0:
            self.conclusion = f"需优化（{warnings}项需关注）"
        else:
            self.conclusion = "完全达标"

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "role": self.role,
            "timestamp": self.timestamp.isoformat(),
            "score": self.score,
            "conclusion": self.conclusion,
            "appeal": self.appeal,
            "reviewer": self.reviewer,
            "items": [
                {"category": i.category, "status": i.status,
                 "detail": i.detail, "suggestion": i.suggestion,
                 "guideline_ref": i.guideline_ref, "evidence": i.evidence}
                for i in self.items
            ],
        }


@dataclass
class FullAuditTrail:
    patient_id: str
    reports: dict[str, StageAuditReport] = field(default_factory=dict)
    overall_score: int = 0
    overall_conclusion: str = "未评估"

    def add_report(self, report: StageAuditReport) -> None:
        self.reports[report.stage_id] = report

    def finalize(self) -> None:
        for r in self.reports.values():
            r.finalize()
        scores = [r.score for r in self.reports.values() if r.items]
        if scores:
            self.overall_score = round(sum(scores) / len(scores))
        conclusions = [r.conclusion for r in self.reports.values() if r.items]
        if any("不达标" in c for c in conclusions):
            self.overall_conclusion = "存在不达标Stage"
        elif any("需优化" in c for c in conclusions):
            self.overall_conclusion = "需优化"
        else:
            self.overall_conclusion = "全部达标"

    def to_dict(self) -> dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "overall_score": self.overall_score,
            "overall_conclusion": self.overall_conclusion,
            "reports": {k: v.to_dict() for k, v in self.reports.items()},
        }
