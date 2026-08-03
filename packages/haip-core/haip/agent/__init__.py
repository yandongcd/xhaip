"""Agent Plugin — DomainPlugin 模型 + YAML loader + Registry."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from haip.llm import DEFAULT_MAX_TOKENS

logger = logging.getLogger(__name__)

AgentType = Literal["business", "specialist", "master_data", "rules", "architecture"]
TrustTier = Literal["deep", "standard", "light"]  # v2.0: Agent分级体系


@dataclass
class ToolDef:
    name: str
    description: str = ""
    handler: str = ""
    input: dict[str, str] = field(default_factory=dict)
    output: dict[str, str] = field(default_factory=dict)
    inference_tier: str = "T0"


@dataclass
class PromptConfig:
    system: str = ""
    temperature: float = 0.3
    max_tokens: int = DEFAULT_MAX_TOKENS


@dataclass
class CitationConfig:
    required: bool = False
    min_sources: int = 1
    min_trust: str = "T2"          # T1 = only T1 citations accepted; T2 = T1 or T2


@dataclass
class GuardConfig:
    triggers: list[str] = field(default_factory=list)
    high_risk_scenarios: list[str] = field(default_factory=list)
    citation: CitationConfig = field(default_factory=CitationConfig)


@dataclass
class UIConfig:
    template: str = ""
    roles: list[dict[str, Any]] = field(default_factory=list)
    sidebar: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class StageDef:
    order: int
    id: str
    label: str
    desc: str = ""
    role: str = ""


# 默认诊疗阶段 — 按 Agent 类型分组
_DEFAULT_STAGES_BUSINESS = [
    {"order": 1, "id": "reg", "label": "登记与初评", "desc": "患者基本信息采集、病史录入、初步评估、分诊判定", "role": "分诊护士 / 接诊医师", "role_ids": ["attending", "nurse"]},
    {"order": 2, "id": "diag", "label": "诊断与分型", "desc": "明确诊断、分型分级、鉴别诊断、辅助检查", "role": "主治医师", "role_ids": ["attending"]},
    {"order": 3, "id": "assess", "label": "综合评估", "desc": "多维度评估（合并症/检验/影像/风险评分/多学科会诊）", "role": "主治医师 / 多学科", "role_ids": ["attending"]},
    {"order": 4, "id": "plan", "label": "方案制定", "desc": "制定个性化治疗方案、用药方案、手术计划", "role": "主治医师 / 科主任", "role_ids": ["attending"]},
    {"order": 5, "id": "exec", "label": "治疗执行", "desc": "执行治疗方案、监测并发症、调整方案", "role": "执行团队", "role_ids": ["attending", "nurse"]},
    {"order": 6, "id": "follow", "label": "随访与康复", "desc": "出院随访计划、康复训练、长期管理", "role": "随访护士 / 康复师", "role_ids": ["attending", "nurse"]},
]
_DEFAULT_STAGES_SPECIALIST = [
    {"order": 1, "id": "evaluate", "label": "专项评估", "desc": "专科评估指标采集、风险评估、量表评分", "role": "专科医师"},
    {"order": 2, "id": "analyze", "label": "风险分析", "desc": "多因素分析、风险分层、预警触发判定", "role": "专科医师"},
    {"order": 3, "id": "recommend", "label": "干预建议", "desc": "基于指南的干预方案推荐、药物调整建议", "role": "专科医师"},
    {"order": 4, "id": "monitor", "label": "疗效监测", "desc": "干预效果跟踪、指标复查、方案调整", "role": "专科医师"},
]
_DEFAULT_STAGES_MASTER = [
    {"order": 1, "id": "collect", "label": "数据汇聚", "desc": "多源数据采集、标准化、质量校验", "role": "数据管理员"},
    {"order": 2, "id": "analyze", "label": "数据分析", "desc": "统计分析、趋势发现、异常检测", "role": "数据分析师"},
    {"order": 3, "id": "report", "label": "报告输出", "desc": "指标看板、报告生成、数据分发", "role": "数据分析师"},
]
_DEFAULT_STAGES_MAP = {
    "business": _DEFAULT_STAGES_BUSINESS,
    "specialist": _DEFAULT_STAGES_SPECIALIST,
    "master_data": _DEFAULT_STAGES_MASTER,
}


def _get_default_stages(agent_type: str) -> list[dict]:
    return _DEFAULT_STAGES_MAP.get(agent_type, _DEFAULT_STAGES_BUSINESS)


def _default_roles(agent_type: str, department: str) -> list[dict]:
    """生成默认角色（当 YAML 未定义 ui.roles 时使用）。"""
    if agent_type == "business":
        base = [
            {"id": "attending", "label": "主治医师", "icon": "🩺"},
            {"id": "nurse", "label": "护士长", "icon": "👩‍⚕️"},
        ]
        if department in ("骨外科", "心血管外科"):
            base.insert(1, {"id": "anesthesiologist", "label": "麻醉师", "icon": "💉"})
        if department == "药剂科":
            base = [
                {"id": "pharmacist", "label": "临床药师", "icon": "💊"},
                {"id": "review_pharmacist", "label": "审方药师", "icon": "📋"},
                {"id": "attending", "label": "主治医师", "icon": "🩺"},
            ]
        return base
    if agent_type == "specialist":
        return [
            {"id": "specialist", "label": "专科医师", "icon": "🔬"},
            {"id": "consultant", "label": "会诊医师", "icon": "🏥"},
        ]
    return [
        {"id": "analyst", "label": "数据分析师", "icon": "📊"},
    ]


@dataclass
class DomainPlugin:
    name: str
    cn_name: str = ""
    version: str = "1.0.0"
    type: AgentType = "business"
    trust_tier: TrustTier = "standard"  # v2.0: deep|standard|light
    department: str = ""
    port: int = 0
    aliases: list[str] = field(default_factory=list)
    prompt: PromptConfig = field(default_factory=PromptConfig)
    tools: list[ToolDef] = field(default_factory=list)
    depends_on: list[dict[str, str]] = field(default_factory=list)
    sub_agents: list[str] = field(default_factory=list)
    parent: str = ""
    guard: GuardConfig = field(default_factory=GuardConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    stages: list[dict[str, Any]] = field(default_factory=list)

    def get_roles(self) -> list[dict]:
        """返回角色列表，YAML 定义优先，否则按 type + department 生成默认。"""
        if self.ui.roles:
            return self.ui.roles
        return _default_roles(self.type, self.department)

    def get_stages(self) -> list[dict]:
        """返回阶段列表，YAML 定义优先，否则按 type 取默认。"""
        if self.stages:
            return self.stages
        return _get_default_stages(self.type)

    @classmethod
    def from_yaml(cls, data: dict[str, Any]) -> DomainPlugin:
        prompt = PromptConfig(**data.get("prompt", {}))
        tools = [ToolDef(**t) for t in data.get("tools", [])]
        guard_data = data.get("guard") or {}
        citation_data = guard_data.get("citation") or {}
        guard = GuardConfig(
            triggers=guard_data.get("triggers", []),
            high_risk_scenarios=guard_data.get("high_risk_scenarios", []),
            citation=CitationConfig(
                required=citation_data.get("required", False),
                min_sources=citation_data.get("min_sources", 1),
                min_trust=citation_data.get("min_trust", "T2"),
            ),
        )
        ui = UIConfig(
            template=data.get("ui", {}).get("template", ""),
            roles=data.get("ui", {}).get("roles", []),
            sidebar=data.get("ui", {}).get("sidebar", []),
        )
        return cls(
            name=data["name"],
            cn_name=data.get("cn_name", ""),
            version=data.get("version", "1.0.0"),
            type=data.get("type", "business"),
            trust_tier=data.get("trust_tier", "standard"),
            department=data.get("department", ""),
            port=data.get("port", 0),
            aliases=data.get("aliases", []),
            prompt=prompt,
            tools=tools,
            depends_on=data.get("depends_on", []),
            sub_agents=data.get("sub_agents", []),
            parent=data.get("parent", ""),
            guard=guard,
            ui=ui,
            stages=data.get("stages", []),
        )


# ── Global Registry ──

_registry: dict[str, DomainPlugin] = {}
_registry_lock = threading.Lock()


def register(plugin: DomainPlugin) -> bool:
    """注册 Agent. 生产模式受 License max_agents 限制 — 超限拒绝注册并返回 False.

    同名校注册视为覆盖更新 (不占新增名额). 开发模式恒放行。
    """
    with _registry_lock:
        if plugin.name in _registry:
            _registry[plugin.name] = plugin
            return True
        from haip.licensing import check_agent_capacity
        allowed, reason = check_agent_capacity(len(_registry))
        if not allowed:
            logger.error("[license] Agent '%s' 注册被拒绝: %s", plugin.name, reason)
            return False
        _registry[plugin.name] = plugin
        return True


def get(name: str) -> DomainPlugin | None:
    return _registry.get(name)


def list_all(include_skipped: bool = False) -> dict[str, DomainPlugin]:
    if include_skipped:
        with _registry_lock:
            return dict(_registry)
    with _registry_lock:
        return {k: v for k, v in _registry.items() if not _is_skipped(k + ".yaml")}


def load_from_dir(definitions_dir: str | Path, agent_filter: str = "",
                  on_register: callable | None = None) -> int:
    """从目录加载 YAML Agent 定义，返回注册数量。
    
    Args:
        definitions_dir: YAML目录路径
        agent_filter: 非空时仅加载指定 agent + depends_on 链 (BFS).
                      用于 per-agent 容器精简部署。
        on_register: 可选回调，在每个Agent注册后调用。
    """
    root = Path(definitions_dir)
    if agent_filter:
        return _load_single_agent(root, agent_filter, on_register)
    return _load_all_agents(root, on_register)


def _is_skipped(filename: str) -> bool:
    return ".deprecated" in filename or ".internal" in filename


def _parse_and_register(yaml_file: Path, on_register) -> DomainPlugin | None:
    with open(yaml_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "name" not in data:
        return None
    plugin = DomainPlugin.from_yaml(data)
    if not register(plugin):
        return None
    if on_register is not None:
        try:
            on_register(plugin)
        except Exception as e:
            import sys
            print(f"[TOGAF] Validation warning for {plugin.name}: {e}", file=sys.stderr)
    return plugin


def _load_all_agents(root: Path, on_register) -> int:
    count = 0
    for yaml_file in sorted(root.glob("*.yaml")):
        if yaml_file.name.startswith("_") or _is_skipped(yaml_file.name):
            continue
        if _parse_and_register(yaml_file, on_register):
            count += 1
    return count


def _load_single_agent(root: Path, agent_name: str, on_register) -> int:
    """BFS 加载指定 agent + depends_on 链."""
    loaded: set[str] = set()
    queue: list[str] = [agent_name]
    count = 0
    while queue:
        name = queue.pop(0)
        if name in loaded:
            continue
        yf = root / f"{name}.yaml"
        if not yf.exists():
            logger.warning("Agent YAML 不存在: %s", yf)
            continue
        plugin = _parse_and_register(yf, on_register)
        if plugin is None:
            continue
        loaded.add(name)
        count += 1
        for dep in plugin.depends_on:
            dep_name = dep.get("agent", "") if isinstance(dep, dict) else str(dep)
            if dep_name and dep_name not in loaded:
                queue.append(dep_name)
    return count


def build_a2a_routes() -> dict[str, str]:
    """从注册表自动生成 A2A 路由表: agent_name → module_path。"""
    routes: dict[str, str] = {}
    for plugin in _registry.values():
        if plugin.tools:
            module = plugin.name.replace("-", "_")
            routes[plugin.name] = f"modules.{module}.handlers"
    return routes
