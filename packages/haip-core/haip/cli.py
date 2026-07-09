"""xhaip CLI — Typer 统一入口."""

from __future__ import annotations

from pathlib import Path

import typer

from haip.agent import load_from_dir, list_all as list_agents, get as get_agent
from haip.a2a import call as a2a_call, get_history

app = typer.Typer(name="xhaip", help="HAIP v1.0 — Hospital AI Platform")

# TOGAF sub-command group
togaf_app = typer.Typer(help="TOGAF 10 Architecture Governance")
app.add_typer(togaf_app, name="togaf")


@app.command()
def list():
    """列出所有已注册的 Agent。"""
    load_all()
    agents = list_agents()
    if not agents:
        typer.echo("No agents registered. Run 'agent load' first.")
        return
    for name, p in agents.items():
        typer.echo(f"  {p.type:14s} | {name:30s} | {p.cn_name}")


@app.command()
def info(name: str = typer.Argument(..., help="Agent 名称")):
    """查看单个 Agent 的详细信息。"""
    load_all()
    p = get_agent(name)
    if p is None:
        typer.echo(f"Unknown agent: {name}")
        return
    typer.echo(f"  Name:        {p.name}")
    typer.echo(f"  Display:     {p.cn_name}")
    typer.echo(f"  Type:        {p.type}")
    typer.echo(f"  Port:        {p.port}")
    typer.echo(f"  Department:  {p.department}")
    typer.echo(f"  Version:     {p.version}")
    typer.echo(f"  Tools:       {len(p.tools)}")
    for t in p.tools:
        typer.echo(f"    - {t.name}: {t.description[:60]}")
    if p.sub_agents:
        typer.echo(f"  Sub-agents:  {', '.join(p.sub_agents)}")
    if p.parent:
        typer.echo(f"  Parent:      {p.parent}")


@app.command()
def call(
    agent: str = typer.Argument(..., help="Agent 名称"),
    tool: str = typer.Argument(..., help="Tool 名称"),
    params: str = typer.Option("{}", help="JSON 格式参数"),
):
    """通过 A2A 调用 Agent 的工具。"""
    import json
    load_all()
    try:
        p = json.loads(params)
    except json.JSONDecodeError:
        typer.echo(f"Invalid JSON params: {params}")
        return
    result = a2a_call(agent, tool, p)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def history(limit: int = typer.Option(10, help="返回条数")):
    """查看 A2A 调用历史。"""
    for h in get_history(limit):
        status = h["status"]
        color = "green" if status == "ok" else "red"
        typer.secho(f"  {h['agent']:25s} | {h['tool']:25s} | {status}", fg=color)


@app.command()
def load():
    """加载所有 YAML Agent 定义到注册表。"""
    load_all()
    agents = list_agents()
    typer.echo(f"Loaded {len(agents)} agents.")


def load_all():
    """Auto-discover YAML definitions directory."""
    candidates = [
        Path.cwd() / "agents" / "definitions",
        Path.cwd() / "packages" / "haip-hospital" / "agents" / "definitions",
    ]
    for d in candidates:
        if d.exists():
            load_from_dir(str(d))
            return


def main():
    app()


# ═══════════════════════════════════════════════════════
# TOGAF Architecture Governance Commands
# ═══════════════════════════════════════════════════════

@togaf_app.command("list")
def togaf_list():
    """列出 TOGAF 元模型（实体类型 + 关系类型 + 可用领域）。"""
    from haip.togaf.metamodel import list_entity_types, list_relationship_types
    from haip.togaf.builder import list_domains as list_builder_domains
    from haip.togaf.templates import list_templates as list_ea_templates

    typer.echo("=== TOGAF Entity Types (10) ===")
    for e in list_entity_types():
        typer.echo(f"  {e['id']:30s} [{e['layer']}] — {e['description']}")

    typer.echo("\n=== TOGAF Relationship Types (13) ===")
    for r in list_relationship_types():
        typer.echo(f"  {r['id']:25s} [{r['category']}] {r['source']} → {r['target']}")

    typer.echo(f"\n=== Builder Domains: {list_builder_domains()} ===")
    typer.echo(f"=== EA Templates: {list_ea_templates()} ===")


@togaf_app.command("build")
def togaf_build(
    domain: str = typer.Argument("orthopedic", help="领域名称 (e.g. orthopedic)"),
):
    """为指定领域生成 4A 架构。"""
    from haip.togaf.builder import build_4a

    arch = build_4a(domain)
    if arch is None:
        typer.echo(f"Unknown domain: {domain}")
        return
    typer.echo(arch.summary())
    for n in arch.nodes():
        typer.echo(f"  [{n.layer:12s}] {n.id:30s} {n.name}")


@togaf_app.command("validate")
def togaf_validate(
    bp: bool = typer.Option(False, "--bp", help="同时运行 BP 治理校验"),
):
    """运行 TOGAF 合规校验（全部已注册 Agent）。"""
    load_all()
    from haip.togaf.validator import print_all_reports

    typer.echo(print_all_reports())

    if bp:
        from haip.togaf.governance import validate_business_processes

        typer.echo("\n--- BP Governance Validation ---")
        result = validate_business_processes()
        for bp_name, checks in result.details.items():
            failed = [c for c in checks if not c.passed]
            if failed:
                typer.echo(f"  {bp_name}: {len(failed)}/{len(checks)} checks FAILED")
                for c in failed:
                    typer.echo(f"    ❌ {c.id}: {c.detail}")
        typer.echo(f"\nBP Governance: {result.checks_passed}/{result.checks_total} checks passed")


@togaf_app.command("arch")
def togaf_arch(
    action: str = typer.Argument("audit", help="audit | show | export"),
    out: str = typer.Option("", "--out", help="Export JSON file path"),
):
    """TOGAF 架构审计: 环境自动发现、查看报告、导出。"""
    if action == "audit":
        from haip.togaf.audit import audit_environment

        stats = audit_environment()
        typer.echo("=== Environment Audit ===")
        for k, v in stats.items():
            typer.echo(f"  {k}: {v}")

    elif action == "show":
        from haip.togaf.audit import auto_discover

        landscape = auto_discover()
        for n in landscape.nodes:
            typer.echo(f"  [{n.type}] {n.id} — {n.name}")
        typer.echo(f"\n  Total: {len(landscape.nodes)} nodes, {len(landscape.edges)} edges")

    elif action == "export":
        from haip.togaf.audit import export_landscape

        path = export_landscape(out or "landscape.json")
        typer.echo(f"Exported to: {path}")

    else:
        typer.echo(f"Unknown action: {action}. Use: audit | show | export")


@togaf_app.command("org")
def togaf_org(
    role_id: str = typer.Option("", "--role", help="查看特定角色"),
    org_id: str = typer.Option("", "--org", help="列出科室角色"),
):
    """查看 TOGAF 组织架构和角色。"""
    from haip.togaf.organization import list_orgs, list_roles, get_role, build_org_tree

    if role_id:
        r = get_role(role_id)
        if r:
            typer.echo(f"Role: {r.name} ({r.org_name}) — {r.level}")
            typer.echo(f"Description: {r.description}")
            typer.echo("Focus Areas:")
            for i, fa in enumerate(r.focus_areas, 1):
                typer.echo(f"  {i}. {fa}")
        else:
            typer.echo(f"Role not found: {role_id}")
        return

    if org_id:
        roles = list_roles(org_id=org_id)
        typer.echo(f"Roles in {org_id} ({len(roles)}):")
        for r in roles:
            typer.echo(f"  {r.id:45s} {r.level:10s}")
        return

    tree = build_org_tree()
    typer.echo(f"Organization Tree ({len(list_orgs())} nodes, {tree.roots[0].children if tree.roots else 0} root categories)")
    for root in tree.roots:
        _print_org_tree(root, indent=0)


def _print_org_tree(node, indent=0):
    prefix = "  " * indent + ("├─ " if indent > 0 else "")
    from haip.togaf.organization import ROLE_BY_ORG
    role_count = len(ROLE_BY_ORG.get(node.id, []))
    role_info = f" ({role_count} roles)" if role_count > 0 else ""
    typer.echo(f"{prefix}{node.name}{role_info}")
    for child in node.children:
        _print_org_tree(child, indent + 1)
