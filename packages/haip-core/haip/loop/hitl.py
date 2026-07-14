"""HITL (Human-in-the-Loop) integration — 高危决策时暂停等待人工确认.

Usage:
    from haip.loop.hitl import HITLHook, HITLRequest
    hooks = HookChain()
    hooks.add("after_agent", HITLHook(required_below=0.3).check)

When guard confidence < threshold or blocked, the hook returns a HITL request
that the caller can handle via the session event system.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from haip.loop.hooks import HookContext


@dataclass
class HITLRequest:
    """HITL 请求 — 由 Agent/Guard 生成，等待人工决策。"""
    agent_name: str = ""
    query: str = ""
    proposed_output: str = ""
    guard_flags: list[str] = field(default_factory=list)
    confidence: float = 0.0
    action_required: str = "confirm_or_reject"  # confirm_or_reject | free_text
    status: str = "pending"  # pending | confirmed | rejected


class HITLHook:
    """HITL 钩子 — after_agent 阶段检查是否需要人工介入。"""

    def __init__(self, required_below: float = 0.3) -> None:
        self.required_below = required_below

    def check(self, ctx: HookContext, reply: str) -> str | None:
        """检查是否需要 HITL。返回修改后的 reply（含 HITL 标记）或 None（无需介入）。"""
        confidence = ctx.metadata.get("confidence", 1.0)
        guard_blocked = ctx.metadata.get("guard_blocked", False)
        guard_flags = ctx.metadata.get("guard_flags", [])

        if confidence < self.required_below or guard_blocked:
            request = HITLRequest(
                agent_name=ctx.agent_name,
                query=ctx.metadata.get("query", ""),
                proposed_output=reply,
                guard_flags=guard_flags,
                confidence=confidence,
                action_required="confirm_or_reject",
            )
            # Store HITL request metadata for the caller
            ctx.metadata["hitl_request"] = request
            ctx.metadata["hitl_pending"] = True
            return (
                f"[HITL PENDING] Agent '{ctx.agent_name}' 置信度 {confidence:.2f}"
                f" 低于阈值 {self.required_below}，"
                f"或存在高危标记: {', '.join(guard_flags)}。"
                f"请人工审核以下输出:\n\n{reply}\n\n"
                f"[提交确认或修改后的输出]"
            )
        return None
