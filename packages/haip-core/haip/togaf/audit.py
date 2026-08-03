"""TOGAF 10 Environment Auto-Audit — filesystem + agent registry → ArchitectureLandscape.

Scans ``packages/haip-hospital/agents/definitions/*.yaml`` for agent definitions,
reads the agent registry (``haip.agent.list_all()``) for runtime state, and builds
a complete TOGAF 10 architecture landscape with nodes and edges.

Exportable to JSON via ``export_landscape()``.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Project root discovery ──

def _find_project_root(start: Path | None = None) -> Path:
    """Walk up from *start* until we find a ``packages/`` dir (xhaip root)."""
    current = (start or Path(__file__).resolve()).parent
    for _ in range(8):
        if (current / "packages" / "haip-core").is_dir():
            return current
        if (current / "packages" / "haip-hospital").is_dir():
            return current
        if current.parent == current:
            break
        current = current.parent
    return Path.cwd()


# ── TOGAF 10 Metamodel — domain colour map ──

_DOMAIN_META: dict[str, tuple[str, str]] = {
    "business":    ("业务架构", "#0a84ff"),
    "data":        ("数据架构", "#5e5ce6"),
    "application": ("应用架构", "#30d158"),
    "technology":  ("技术架构", "#ff453a"),
}

_AGENT_TYPE_LAYER: dict[str, tuple[str, str]] = {
    "business":      ("ApplicationComponent", "application"),
    "specialist":    ("ApplicationService",   "application"),
    "master_data":   ("DataEntity",           "data"),
    "rules":         ("ApplicationComponent", "application"),
    "architecture":  ("ApplicationComponent", "application"),
}


# ── Data Models ──


@dataclass
class ArchNode:
    """A TOGAF 10 architecture entity instance (real deployment artifact)."""

    id: str
    label: str
    entity_type: str
    domain: str
    group: str = ""
    color: str = "#888"
    icon: str = "●"
    description: str = ""
    properties: dict[str, str] = field(default_factory=dict)


@dataclass
class ArchEdge:
    """A TOGAF 10 relationship between two architecture entities."""

    source: str
    target: str
    relationship_type: str
    label: str = ""
    description: str = ""


@dataclass
class ArchitectureLandscape:
    """Full TOGAF 10 architecture landscape for the deployed environment."""

    name: str = "xHAIP 平台架构景观"
    description: str = "真实部署环境 — 南方医院 xHAIP 平台 TOGAF 10 架构景观"
    nodes: list[ArchNode] = field(default_factory=list)
    edges: list[ArchEdge] = field(default_factory=list)

    def node_by_id(self, nid: str) -> ArchNode | None:
        for n in self.nodes:
            if n.id == nid:
                return n
        return None


# ── Serialization ──


def _landscape_to_dict(landscape: ArchitectureLandscape) -> dict[str, Any]:
    return {
        "name": landscape.name,
        "description": landscape.description,
        "nodes": [asdict(n) for n in landscape.nodes],
        "edges": [asdict(e) for e in landscape.edges],
    }


def _landscape_from_dict(data: dict[str, Any]) -> ArchitectureLandscape:
    nodes = [ArchNode(**n) for n in data.get("nodes", [])]
    edges = [ArchEdge(**e) for e in data.get("edges", [])]
    return ArchitectureLandscape(
        name=data.get("name", ""),
        description=data.get("description", ""),
        nodes=nodes,
        edges=edges,
    )


# ── Paths ──


def _definitions_dir(project_root: Path) -> Path:
    return project_root / "packages" / "haip-hospital" / "agents" / "definitions"


def _knowledge_dir(project_root: Path) -> Path:
    return project_root / "packages" / "haip-hospital" / "knowledge"


# ── Auto-Discovery ──


def auto_discover(project_root: Path | None = None) -> ArchitectureLandscape:
    """Scan filesystem + agent registry to build a complete ArchitectureLandscape.

    Discovers:
      * Organization node (南方医院)
      * YAML-defined agents from ``agents/definitions/*.yaml``
      * Agent registry entries (``haip.agent.list_all()``)
      * Data entities from ``knowledge/`` directory
      * Technology components (Python runtime, OS)
      * Relationships between all discovered entities
    """
    root = project_root or _find_project_root()
    landscape = ArchitectureLandscape()
    seen: set[str] = set()

    # ── 1. Organization ──
    _discover_organization(landscape, seen)

    # ── 2. Agent definitions from YAML ──
    _discover_agents_from_yaml(landscape, seen, root)

    # ── 3. Agent registry (runtime) ──
    _discover_agents_from_registry(landscape, seen)

    # ── 4. Knowledge / Data entities ──
    _discover_knowledge_assets(landscape, seen, root)

    # ── 5. Technology components ──
    _discover_technology(landscape, seen)

    # ── 6. Relationships ──
    _build_relationships(landscape)

    return landscape


def audit_environment(project_root: Path | None = None) -> dict[str, Any]:
    """Run auto-discover and return a stats dict about what was found.

    Returns a dict with keys:
      * landscape — the ArchitectureLandscape (serialisable)
      * stats — counts by entity_type and domain
      * edges_total — total relationship count
      * registry_size — number of agents in the in-memory registry
      * yaml_count — number of YAML files scanned
    """
    root = project_root or _find_project_root()
    landscape = auto_discover(root)

    stats: dict[str, int] = {}
    for node in landscape.nodes:
        stats[node.entity_type] = stats.get(node.entity_type, 0) + 1

    yaml_count = len(list(_definitions_dir(root).glob("*.yaml")))
    try:
        from haip.agent import list_all
        registry_size = len(list_all())
    except Exception:
        logger.debug("Agent list_all failed", exc_info=True)
        registry_size = 0

    return {
        "landscape": _landscape_to_dict(landscape),
        "stats": stats,
        "edges_total": len(landscape.edges),
        "nodes_total": len(landscape.nodes),
        "registry_size": registry_size,
        "yaml_count": yaml_count,
        "project_root": str(root),
    }


def export_landscape(filepath: str | Path, project_root: Path | None = None) -> str:
    """Auto-discover and export the full landscape as JSON to *filepath*.

    Returns the resolved output path.
    """
    landscape = auto_discover(project_root)
    data = _landscape_to_dict(landscape)
    out = Path(filepath).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out)


# ── Discovery helpers ──


def _discover_organization(landscape: ArchitectureLandscape, seen: set[str]) -> None:
    """Add Southern Hospital organisation node."""
    org = ArchNode(
        id="nfh",
        label="南方医科大学南方医院",
        entity_type="Organization",
        domain="business",
        color="#0a84ff",
        icon="🏢",
        description="三级甲等综合医院 · 2225 床位 · 50+ 临床科室",
        properties={
            "id": "nfh",
            "院长": "孙剑",
            "类型": "三级甲等综合医院",
            "床位数": "2225",
        },
    )
    landscape.nodes.append(org)
    seen.add("nfh")


def _discover_agents_from_yaml(
    landscape: ArchitectureLandscape,
    seen: set[str],
    root: Path,
) -> None:
    """Scan ``agents/definitions/*.yaml`` and create nodes for every agent."""
    defs_dir = _definitions_dir(root)
    if not defs_dir.is_dir():
        return

    import yaml

    for yaml_file in sorted(defs_dir.glob("*.yaml")):
        if yaml_file.name.startswith("_"):
            continue
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception:
            continue
        if not isinstance(data, dict) or "name" not in data:
            continue

        name = data["name"]
        entity_type, domain = _AGENT_TYPE_LAYER.get(
            data.get("type", "business"), ("ApplicationComponent", "application")
        )

        _, color = _DOMAIN_META.get(domain, ("", "#888"))
        icon = _icon_for_agent(data.get("type", "business"))

        port = data.get("port", 0)
        tool_count = len(data.get("tools", []))
        sub_count = len(data.get("sub_agents", []))
        dep_count = len(data.get("depends_on", []))

        desc_parts = [data.get("cn_name", name), f"类型: {data.get('type', 'business')}"]
        if port:
            desc_parts.append(f"端口: {port}")
        if tool_count:
            desc_parts.append(f"{tool_count} 个工具")
        if sub_count:
            desc_parts.append(f"{sub_count} 个子 Agent")

        node = ArchNode(
            id=f"agent-{name}",
            label=data.get("cn_name", name),
            entity_type=entity_type,
            domain=domain,
            group=data.get("department", ""),
            color=color,
            icon=icon,
            description=" · ".join(desc_parts),
            properties={
                "name": name,
                "type": data.get("type", "business"),
                "department": data.get("department", ""),
                "port": str(port) if port else "—",
                "tools": str(tool_count),
                "sub_agents": str(sub_count),
                "depends_on": str(dep_count),
                "version": data.get("version", "1.0.0"),
                "file": str(yaml_file.relative_to(root)),
            },
        )
        landscape.nodes.append(node)
        seen.add(f"agent-{name}")


def _discover_agents_from_registry(
    landscape: ArchitectureLandscape,
    seen: set[str],
) -> None:
    """Check the in-memory agent registry for any agents not already in the landscape."""
    try:
        from haip.agent import list_all
        registered = list_all()
    except Exception:
        return

    for agent_name, plugin in registered.items():
        nid = f"agent-{agent_name}"
        if nid in seen:
            # Merge registry info into existing node
            node = landscape.node_by_id(nid)
            if node:
                _merge_registry_props(node, plugin)
            continue

        entity_type, domain = _AGENT_TYPE_LAYER.get(
            plugin.type, ("ApplicationComponent", "application")
        )
        _, color = _DOMAIN_META.get(domain, ("", "#888"))
        icon = _icon_for_agent(plugin.type)

        port_str = f":{plugin.port}" if plugin.port else ""
        desc = f"{plugin.cn_name} · 类型: {plugin.type}{port_str}"

        node = ArchNode(
            id=nid,
            label=plugin.cn_name or agent_name,
            entity_type=entity_type,
            domain=domain,
            group=plugin.department,
            color=color,
            icon=icon,
            description=desc,
            properties={
                "name": agent_name,
                "type": plugin.type,
                "department": plugin.department,
                "port": str(plugin.port) if plugin.port else "—",
                "tools": str(len(plugin.tools)),
                "sub_agents": str(len(plugin.sub_agents)),
                "version": plugin.version,
                "source": "registry",
            },
        )
        landscape.nodes.append(node)
        seen.add(nid)


def _merge_registry_props(node: ArchNode, plugin: Any) -> None:
    """Add registry-sourced fields to an existing YAML-discovered node."""
    node.properties["tools_registry"] = str(len(plugin.tools))
    node.properties["version_registry"] = plugin.version
    if node.properties.get("port") in ("—", "0") and plugin.port:
        node.properties["port"] = str(plugin.port)


def _discover_knowledge_assets(
    landscape: ArchitectureLandscape,
    seen: set[str],
    root: Path,
) -> None:
    """Discover knowledge/ data entities — guidelines, rules, business processes, etc."""
    knowledge = _knowledge_dir(root)
    if not knowledge.is_dir():
        return

    # Count files per category
    categories: dict[str, tuple[str, str, str]] = {
        "guidelines":       ("临床指南知识库", "📚", "#5e5ce6"),
        "rules":            ("规则引擎知识库", "📐", "#5e5ce6"),
        "business_processes": ("业务流程库", "🔄", "#5e5ce6"),
        "value_streams":    ("价值流定义", "🌊", "#5e5ce6"),
        "capabilities":     ("能力目录", "🎯", "#5e5ce6"),
        "guideline_sources": ("指南来源注册", "📖", "#5e5ce6"),
        "roles":            ("角色定义库", "👤", "#5e5ce6"),
        "architecture":     ("架构实例", "🏗️", "#5e5ce6"),
    }

    for cat_dir_name, (label, icon, color) in categories.items():
        cat_path = knowledge / cat_dir_name
        if not cat_path.is_dir():
            continue
        file_count = sum(
            1 for f in cat_path.rglob("*")
            if f.is_file() and not f.name.startswith(".")
        )
        if file_count == 0:
            continue

        de = ArchNode(
            id=f"de-{cat_dir_name}",
            label=label,
            entity_type="DataEntity",
            domain="data",
            color=color,
            icon=icon,
            description=f"{label} · {file_count} 个文件",
            properties={
                "category": cat_dir_name,
                "path": str(cat_path.relative_to(root)),
                "files": str(file_count),
            },
        )
        landscape.nodes.append(de)
        seen.add(f"de-{cat_dir_name}")


def _discover_technology(
    landscape: ArchitectureLandscape,
    seen: set[str],
) -> None:
    """Add Python runtime and host OS technology components."""
    tc_python = ArchNode(
        id="tc-python",
        label=f"Python {sys.version_info.major}.{sys.version_info.minor}",
        entity_type="TechnologyComponent",
        domain="technology",
        color="#ff453a",
        icon="🐍",
        description=f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} 运行环境",
        properties={
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "path": sys.executable,
            "platform": sys.platform,
        },
    )
    landscape.nodes.append(tc_python)
    seen.add("tc-python")

    tc_os = ArchNode(
        id="tc-os",
        label="Windows 11" if sys.platform == "win32" else sys.platform,
        entity_type="TechnologyComponent",
        domain="technology",
        color="#8b949e",
        icon="🪟" if sys.platform == "win32" else "🖥️",
        description=f"主机操作系统 ({sys.platform})",
        properties={
            "platform": sys.platform,
            "arch": "x64",
        },
    )
    landscape.nodes.append(tc_os)
    seen.add("tc-os")

    tc_yaml = ArchNode(
        id="tc-yaml-store",
        label="YAML 配置存储",
        entity_type="TechnologyComponent",
        domain="technology",
        color="#ff9f0a",
        icon="📄",
        description="Agent 定义 · 知识库 · 规则 — YAML 格式存储",
        properties={
            "format": "YAML",
            "use": "agent definitions, knowledge, rules",
        },
    )
    landscape.nodes.append(tc_yaml)
    seen.add("tc-yaml-store")


# ── Relationship builder ──


def _build_relationships(landscape: ArchitectureLandscape) -> None:
    """Build edges between all discovered nodes."""
    seen_edges: set[tuple[str, str, str]] = set()
    node_ids = {n.id for n in landscape.nodes}

    def _add_edge(src: str, tgt: str, rel: str, label: str, desc: str = "") -> None:
        if src not in node_ids or tgt not in node_ids:
            return
        key = (src, tgt, rel)
        if key in seen_edges:
            return
        seen_edges.add(key)
        landscape.edges.append(ArchEdge(
            source=src, target=tgt,
            relationship_type=rel, label=label, description=desc,
        ))

    # Organization → Agent (has)
    for node in landscape.nodes:
        if node.entity_type in ("ApplicationComponent", "ApplicationService"):
            src_node = landscape.node_by_id("nfh")
            src_label = src_node.label if src_node else "南方医院"
            _add_edge(
                "nfh", node.id, "has", "包含",
                f"{src_label} 部署 {node.label}",
            )

    # Agent → Python runtime (runs_on)
    for node in landscape.nodes:
        if node.entity_type in ("ApplicationComponent", "ApplicationService"):
            _add_edge(
                node.id, "tc-python", "runs_on", "运行于",
                f"{node.label} 运行在 Python 上",
            )

    # Python → OS (deployed_on)
    _add_edge(
        "tc-python", "tc-os", "deployed_on", "部署于",
        "Python 运行在操作系统上",
    )

    # Agent → Agent (depends_on from registry / YAML depends_on)
    try:
        from haip.agent import list_all
        agents = list_all()
        for agent_name, plugin in agents.items():
            src_id = f"agent-{agent_name}"
            if src_id not in node_ids:
                continue
            for dep in plugin.depends_on:
                dep_name = dep.get("agent", "") if isinstance(dep, dict) else dep
                tgt_id = f"agent-{dep_name}"
                _add_edge(
                    src_id, tgt_id, "communicates_via", "A2A 通信",
                    f"{plugin.cn_name or agent_name} → A2A → {dep_name}",
                )
    except Exception:
        logger.debug("Agent A2A edge build failed", exc_info=True)
    for node in landscape.nodes:
        sub_count = node.properties.get("sub_agents", "0")
        if sub_count == "0":
            continue
        try:
            from haip.agent import get as get_plugin
            plugin = get_plugin(node.properties.get("name", ""))
            if plugin and plugin.sub_agents:
                for sub_name in plugin.sub_agents:
                    _add_edge(
                        node.id, f"agent-{sub_name}", "composed_of", "路由",
                        f"{node.label} 路由到 {sub_name}",
                    )
        except Exception:
            logger.debug("Sub-agent edge build failed", exc_info=True)
    for node in landscape.nodes:
        if node.entity_type == "DataEntity":
            for agent_node in landscape.nodes:
                if agent_node.entity_type in ("ApplicationComponent", "ApplicationService"):
                    _add_edge(
                        agent_node.id, node.id, "accesses", "使用",
                        f"{agent_node.label} 访问 {node.label}",
                    )

    # Technology component relationships
    for node in landscape.nodes:
        if node.entity_type == "DataEntity":
            _add_edge(
                node.id, "tc-yaml-store", "stored_on", "存储于",
                f"{node.label} 存储在 YAML",
            )


# ── Icons ──


def _icon_for_agent(agent_type: str) -> str:
    return {
        "business":      "🤖",
        "specialist":    "🔬",
        "master_data":   "💾",
        "rules":         "📐",
        "architecture":  "🏗️",
    }.get(agent_type, "🤖")


# ── CLI integration ──


def main_cli(args: list[str] | None = None) -> None:
    """``haip arch`` CLI subcommand — called from haip CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="xHAIP Architecture Audit (TOGAF 10)",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("audit", help="Auto-discover real deployed environment")
    sub.add_parser("show", help="Print architecture landscape report")
    p_export = sub.add_parser("export", help="Export landscape as JSON")
    p_export.add_argument("--out", default="", help="Output file path")

    sub.add_parser("stats", help="Show audit stats")

    parsed = parser.parse_args(args)

    if parsed.command == "audit":
        print("Auditing environment ...")
        result = audit_environment()
        print(f"  Agents (YAML):    {result['yaml_count']}")
        print(f"  Agents (registry): {result['registry_size']}")
        print(f"  Nodes:             {result['nodes_total']}")
        print(f"  Edges:             {result['edges_total']}")
        for k, v in sorted(result["stats"].items()):
            print(f"  {k:28s}: {v}")

    elif parsed.command == "show":
        landscape = auto_discover()
        print(_report_text(landscape))

    elif parsed.command == "export":
        out = parsed.out or "xhaip_landscape_export.json"
        path = export_landscape(out)
        print(f"Exported to: {path}")

    elif parsed.command == "stats":
        result = audit_environment()
        print(json.dumps({k: v for k, v in result.items() if k != "landscape"},
                         ensure_ascii=False, indent=2))

    else:
        parser.print_help()


def _report_text(landscape: ArchitectureLandscape) -> str:
    lines: list[str] = []
    lines.append(f"# {landscape.name}")
    lines.append(f"  {landscape.description}")
    lines.append("")
    lines.append(f"## 节点 ({len(landscape.nodes)} 个)")
    lines.append("")

    by_domain: dict[str, list[ArchNode]] = {}
    for n in landscape.nodes:
        by_domain.setdefault(n.domain, []).append(n)

    for domain, (label, _) in _DOMAIN_META.items():
        nodes = by_domain.get(domain, [])
        if not nodes:
            continue
        lines.append(f"  --- {label} ---")
        for n in nodes:
            lines.append(f"  [{n.entity_type:24s}] {n.icon} {n.label:28s} | {n.description}")

    lines.append("")
    lines.append(f"## 关系 ({len(landscape.edges)} 条)")
    lines.append("")
    for e in landscape.edges:
        src = landscape.node_by_id(e.source)
        tgt = landscape.node_by_id(e.target)
        src_l = src.label if src else e.source
        tgt_l = tgt.label if tgt else e.target
        lines.append(f"  {src_l:28s} ──{e.label}──▶ {tgt_l}")

    lines.append("")
    lines.append("## 统计")
    for n in landscape.nodes:
        pass  # stats already in audit_environment
    return "\n".join(lines)


if __name__ == "__main__":
    main_cli()
