"""Pre-LLM routing hooks — keyword-based fast path that bypasses LLM for known queries.

Usage:
    from haip.loop.routing import KeywordRouter
    router = KeywordRouter.from_yaml("routing.yaml")
    hooks = HookChain()
    hooks.add("before_agent", router.match)

Config YAML format:
    routes:
      - keywords: [NRS2002, 营养风险筛查, 营养评估]
        agent: pharmacy
        tool: assess_nutrition
        priority: 100
      - keywords: [ASA分级, ASA 分级, 麻醉分级]
        agent: anesthesia-risk
        tool: assess_asa
      - keywords: [ECG, 心电图, 心电判读]
        agent: cardio-risk
        tool: interpret_ecg
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from haip.loop.hooks import HookContext


@dataclass
class RouteRule:
    keywords: list[str] = field(default_factory=list)
    agent: str = ""
    tool: str = ""
    priority: int = 0
    reply_template: str = ""


class KeywordRouter:
    """关键词路由 — 匹配即转发，跳过 LLM。

    使用示例:
        hooks = HookChain()
        router = KeywordRouter()
        router.add("NRS2002", "pharmacy", "assess_nutrition")
        hooks.add("before_agent", router.match)
    """

    def __init__(self) -> None:
        self._routes: list[RouteRule] = []

    def add(self, keyword: str, agent: str, tool: str, priority: int = 0) -> None:
        self._routes.append(RouteRule(
            keywords=[keyword.lower()],
            agent=agent,
            tool=tool,
            priority=priority,
        ))

    def add_batch(self, keywords: list[str], agent: str, tool: str, priority: int = 0) -> None:
        self._routes.append(RouteRule(
            keywords=[k.lower() for k in keywords],
            agent=agent,
            tool=tool,
            priority=priority,
        ))

    @classmethod
    def from_yaml(cls, path: str | Path) -> KeywordRouter:
        """从 YAML 加载路由配置."""
        router = cls()
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for route in data.get("routes", []):
                router._routes.append(RouteRule(
                    keywords=[k.lower() for k in route.get("keywords", [])],
                    agent=route.get("agent", ""),
                    tool=route.get("tool", ""),
                    priority=route.get("priority", 0),
                    reply_template=route.get("reply_template", ""),
                ))
        except (FileNotFoundError, yaml.YAMLError):
            pass
        return router

    def match(self, ctx: HookContext) -> str | None:
        """before_agent hook — 匹配后返回路由指令 (跳过 Agent)。"""
        query = ctx.metadata.get("query", "").lower()
        if not query:
            return None
        matched = []
        for route in self._routes:
            for kw in route.keywords:
                if kw in query:
                    matched.append(route)
                    break
        if not matched:
            return None
        # 按优先级排序，取最高
        matched.sort(key=lambda r: r.priority, reverse=True)
        best = matched[0]
        return (
            f"__ROUTE__:{best.agent}:{best.tool}"
            if not best.reply_template
            else best.reply_template
        )
