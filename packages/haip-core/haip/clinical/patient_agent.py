"""虚拟病人 Agent (L5) — LLM驱动的患者 persona, 支持多轮对话 + 病情转归.

设计: 患者 agent 可回答医生追问、报告症状变化、接受治疗方案.
honesty_level 控制隐瞒/遗忘概率 (MED-5 对抗行为).
"""

from __future__ import annotations

from typing import Any

from haip.clinical.progression import PatientState, ProgressionEngine, ProgressionRule


class PatientAgent:
    """虚拟病人 — 可多轮对话的 LLM 驱动的患者."""

    def __init__(self, patient: dict[str, Any], progression: ProgressionEngine | None = None,
                 honesty_level: float = 1.0, seed: int | None = 42):
        self.patient = patient
        self.pid = patient.get("patient_id", "?")
        self.diagnosis = patient.get("diagnosis", "")
        self.age = patient.get("age", 0)
        self.gender = patient.get("gender", "")
        self.labs = patient.get("lab_results") or {}
        self.scenario = patient.get("scenario", "")
        self.symptoms = patient.get("scenario", "") or "需进一步问诊"

        self.honesty = honesty_level  # 0.5=可能隐瞒 1.0=完全坦诚
        self.progression = progression or ProgressionEngine(seed=seed)
        self.state = PatientState.STABLE
        self.day = 0
        self.history: list[dict[str, Any]] = []

    def _build_system_prompt(self) -> str:
        """患者 persona 系统提示词."""
        base = (
            f"你是一名{self.age}岁{self.gender}患者。你的诊断是'{self.diagnosis}'。"
            f"你的主要症状: {self.symptoms}。"
            "请以患者的口吻回答医生的问题。描述你的感受、症状变化。"
        )
        if self.honesty < 0.8:
            base += f" (你可能遗忘或隐瞒部分信息 — 当前坦诚度 {self.honesty:.0%})"
        if self.state != PatientState.STABLE:
            state_cn = self.progression.state_display(self.state)
            base += f" 你的当前状态: {state_cn}。"
        return base

    def complain(self, provider: Any = None) -> str:
        """患者主动主诉 (首次就诊 / 复诊)."""
        prompt = self._build_system_prompt()
        if self.day == 0:
            prompt += "\n请描述你为什么来医院。"
        else:
            prompt += f"\n你已经治疗了{self.day}天。请描述你现在的感受和变化。"

        if provider:
            try:
                resp = provider.chat(
                    messages=[{"role": "system", "content": prompt},
                              {"role": "user", "content": "你好, 请问今天感觉怎么样?"}],
                    temperature=0.5, max_tokens=300,
                )
                return resp.content or self._fallback_complaint()
            except Exception:
                pass

        return self._fallback_complaint()

    def _fallback_complaint(self) -> str:
        if self.day == 0:
            return f"{self.diagnosis}, {self.symptoms} (坦诚度 {self.honesty:.0%})"
        return f"治疗{self.day}天后, 恢复情况: {self.progression.state_display(self.state)}"

    def answer_question(self, question: str, provider: Any = None) -> str:
        """回答医生的追问."""
        prompt = self._build_system_prompt()
        prompt += f"\n医生的追问: {question}\n请以患者的口吻如实回答。"

        if provider:
            try:
                resp = provider.chat(
                    messages=[{"role": "system", "content": prompt},
                              {"role": "user", "content": question}],
                    temperature=0.5, max_tokens=200,
                )
                return resp.content or self._fallback_answer(question)
            except Exception:
                pass

        return self._fallback_answer(question)

    def _fallback_answer(self, question: str) -> str:
        lab_highlights = ", ".join(f"{k}={v}" for k, v in list(self.labs.items())[:5])
        return (f"回答'{question}': 诊断 {self.diagnosis}, "
                f"检验: {lab_highlights or '未查'}, 状态: {self.progression.state_display(self.state)}")

    def receive_treatment(self, action: str, condition: str = "") -> tuple[PatientState, ProgressionRule | None]:
        """医生给出治疗方案后, 计算转归."""
        new_state, rule = self.progression.next_state(self.state, condition or action)
        old = self.state
        self.state = new_state
        self.history.append({
            "day": self.day, "action": action, "condition": condition,
            "old_state": old.value, "new_state": new_state.value,
            "guideline_ref": rule.guideline_ref if rule else "",
        })
        return (new_state, rule)

    def progress_day(self) -> None:
        """推进一天 (病情自然演进)."""
        self.day += 1

    def is_alive(self) -> bool:
        return self.state != PatientState.DECEASED

    def is_recovered(self) -> bool:
        return self.state == PatientState.RECOVERED

    def summary(self) -> dict[str, Any]:
        return {
            "patient_id": self.pid,
            "diagnosis": self.diagnosis,
            "state": self.state.value,
            "day": self.day,
            "transitions": self.history,
            "final_outcome": self.progression.state_display(self.state),
        }


def run_consultation(patient: PatientAgent, agent_name: str, max_rounds: int = 3,
                     provider: Any = None) -> dict[str, Any]:
    """模拟一次完整的医患会诊: 患者主诉 → 医生追问×N → 方案 → 转归."""
    from haip.a2a import reason

    # 第1轮: 患者主诉
    complaint = patient.complain(provider)

    # 医生推理 (agentic)
    diagnosis_result = reason(agent_name, complaint, max_steps=3, provider=provider)

    # 基于推理结果选择治疗方案
    urgency = diagnosis_result.get("urgency", "")
    if urgency == "emergency":
        action = "急诊手术在48h内完成"
    elif urgency == "elective":
        action = "手术延迟 >48h"
    else:
        action = "保守治疗 (无手术)"

    # 转归
    new_state, rule = patient.receive_treatment(action)
    patient.progress_day()

    return {
        "patient": patient.summary(),
        "agent_response": diagnosis_result,
        "treatment_action": action,
        "new_state": new_state.value,
        "rule_applied": rule.rule_id if rule else "default",
        "guideline_ref": rule.guideline_ref if rule else "",
    }
