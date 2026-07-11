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

# Tools sub-command group
tools_app = typer.Typer(help="Tools: MCP server, registry")
app.add_typer(tools_app, name="tools")

# Release sub-command group
release_app = typer.Typer(help="Release & baseline management")
app.add_typer(release_app, name="release")

# Audit sub-command group
audit_app = typer.Typer(help="Audit & recovery (snapshot, diff, rollback)")
app.add_typer(audit_app, name="audit")


@app.command("list")
def list_agents_cmd():
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


# ═══════════════════════════════════════════════════════
# Skill Sync Commands
# ═══════════════════════════════════════════════════════

@app.command()
def sync_skills(
    apply: bool = typer.Option(False, "--apply", help="Execute sync (default: dry-run)"),
    validate: bool = typer.Option(False, "--validate", help="Validate sync consistency"),
    init: bool = typer.Option(False, "--init", help="Initialize: copy runtime -> source"),
    list_skills: bool = typer.Option(False, "--list", "-l", help="List all skills"),
):
    """Sync skills between agent source modules and .openharness/skills/."""
    from haip.operations.skill_sync import (
        sync as do_sync,
        validate as do_validate,
        init_from_runtime,
        list_skills as do_list,
    )

    if validate:
        exit_code = do_validate()
        raise typer.Exit(code=exit_code)
    if init:
        exit_code = init_from_runtime()
        raise typer.Exit(code=exit_code)
    if list_skills:
        import json
        result = do_list()
        typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    do_sync(dry_run=not apply)


# ═══════════════════════════════════════════════════════
# Tools Commands
# ═══════════════════════════════════════════════════════

@tools_app.command("mcp-serve")
def tools_mcp_serve(
    agent: str = typer.Option("", "--agent", "-a", help="Serve single agent's tools"),
    all_tools: bool = typer.Option(False, "--all", help="Serve all registered tools"),
    port: int = typer.Option(8700, "--port", "-p", help="Port (default: 8700)"),
    host: str = typer.Option("0.0.0.0", "--host", help="Host (default: 0.0.0.0)"),
):
    """Start MCP server exposing agent tools."""
    from haip.tools.mcp_server import serve_agent, serve_all

    load_all()
    if all_tools:
        serve_all(port=port, host=host)
    elif agent:
        serve_agent(agent, port=port, host=host)
    else:
        typer.echo("Specify --agent <name> or --all", err=True)
        raise typer.Exit(code=1)


@tools_app.command("list")
def tools_list(
    agent: str = typer.Option("", "--agent", "-a", help="Filter by agent name"),
):
    """List tools from registry or specific agent."""
    load_all()
    from haip.tools.registry import list_schemas

    if agent:
        plugin = get_agent(agent)
        if plugin is None:
            typer.echo(f"Unknown agent: {agent}")
            return
        tools = plugin.tools
        typer.echo(f"Agent '{agent}' ({plugin.cn_name}) — {len(tools)} tools:")
        for td in tools:
            typer.echo(f"  {td.name:30s} | {td.description[:60]}")
        return

    registry_tools = list_schemas()
    all_agents = list_agents()
    typer.echo(f"Global Tool Registry: {len(registry_tools)} tools")
    for t in registry_tools:
        typer.echo(f"  {t['name']:30s} | {t.get('description', '')[:60]}")

    if all_agents:
        typer.echo(f"\nAgent Tools ({len(all_agents)} agents):")
        for aname, ainfo in sorted(all_agents.items()):
            tnames = [t.name for t in ainfo.tools]
            if tnames:
                typer.echo(f"  {aname:30s} | {len(tnames)} tools: {', '.join(tnames[:5])}{'...' if len(tnames) > 5 else ''}")


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


# ═══════════════════════════════════════════════════════
# Release / Baseline Management Commands
# ═══════════════════════════════════════════════════════

@release_app.command("backup")
def release_backup(
    label: str = typer.Option("", "--label", "-l", help="Optional label for this backup"),
):
    """Create a named backup of agent definitions, modules, knowledge, and config."""
    from haip.operations.release_manager import ReleaseManager

    rm = ReleaseManager()
    result = rm.create_backup(label=label)
    backup_id = result.get("backup_id", "")

    typer.echo(f"Backup created: {backup_id}")
    typer.echo(f"  Location: releases/{backup_id}/")
    typer.echo(f"  Files: {len(result.get('files', {}))}")
    typer.echo(f"  Commit: {(result.get('commit', '') or '')[:12]}")
    typer.echo(f"  Branch: {result.get('branch', '')}")


@release_app.command("list")
def release_list():
    """List all backups."""
    from haip.operations.release_manager import ReleaseManager

    rm = ReleaseManager()
    backups = rm.list_backups()
    if not backups:
        typer.echo("No backups found.")
        return
    typer.echo(f"{'Backup ID':<35} {'Date':<12} {'Commit':<14} {'Branch':<12} {'Files':<6} Message")
    typer.echo("-" * 100)
    for b in backups:
        typer.echo(
            f"{b['backup_id']:<35} {b['date']:<12} {b['commit']:<14} "
            f"{b['branch']:<12} {b['total_files']:<6} {b['message']}"
        )


@release_app.command("rollback")
def release_rollback(
    backup_id: str = typer.Argument(..., help="Backup ID to restore from"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Restore project files from a backup."""
    from haip.operations.release_manager import ReleaseManager

    rm = ReleaseManager()
    info = rm.info(backup_id)
    if info is None:
        typer.echo(f"Backup not found: {backup_id}")
        return

    typer.echo(f"Backup: {backup_id}")
    typer.echo(f"  Date: {info.get('date', '')}")
    typer.echo(f"  Files: {len(info.get('files', {}))}")
    typer.echo()

    if not force:
        confirm = typer.confirm("Proceed with rollback?")
        if not confirm:
            typer.echo("Rollback cancelled.")
            return

    result = rm.rollback(backup_id)
    for p in result.get("restored", []):
        typer.echo(f"  RESTORED {p}")
    for p in result.get("errors", []):
        typer.secho(f"  ERROR {p}", fg="red")
    for p in result.get("skipped", []):
        typer.secho(f"  SKIPPED {p}", fg="yellow")
    typer.echo(f"\nDone: {len(result.get('restored', []))} restored, "
               f"{len(result.get('errors', []))} errors.")


# ═══════════════════════════════════════════════════════
# Audit & Recovery Commands
# ═══════════════════════════════════════════════════════

@audit_app.command("snapshot")
def audit_snapshot(
    paths: list[str] = typer.Argument(..., help="File paths (relative to project root)"),
    agent: str = typer.Option("", "--agent", help="Agent name"),
    reason: str = typer.Option("", "--reason", help="Reason for snapshot"),
):
    """Create a checksum snapshot of specified files."""
    from haip.operations.audit_release import AuditEngine

    ae = AuditEngine()
    snap_id = ae.snapshot(*paths, agent=agent, reason=reason)
    typer.echo(f"Snapshot created: {snap_id}")
    typer.echo(f"  Files: {len(paths)}")
    typer.echo(f"  Agent: {agent or '(unspecified)'}")
    typer.echo(f"  Reason: {reason or '(unspecified)'}")


@audit_app.command("list")
def audit_list():
    """List recent snapshots."""
    from haip.operations.audit_release import AuditEngine

    ae = AuditEngine()
    snaps = ae.list_snapshots()
    if not snaps:
        typer.echo("No snapshots found.")
        return
    typer.echo(f"{'Snap ID':<30} {'Time':<28} {'Agent':<20} {'Files':<6} Reason")
    typer.echo("-" * 100)
    for s in snaps:
        typer.echo(f"{s['snap_id']:<30} {s['time']:<28} {s['agent']:<20} "
                    f"{s['file_count']:<6} {s['reason']}")


@audit_app.command("diff")
def audit_diff(
    snap_id: str = typer.Argument(..., help="Snapshot ID to diff against current state"),
    snap2: str = typer.Option("", "--snap2", help="Second snapshot ID for pairwise comparison"),
):
    """Compare snapshot against current state, or diff two snapshots."""
    from haip.operations.audit_release import AuditEngine

    ae = AuditEngine()

    if snap2:
        diffs = ae.diff_two(snap_id, snap2)
    else:
        diffs = ae.diff(snap_id)

    for d in diffs:
        if d.get("error"):
            typer.secho(f"ERROR {d['file']}: {d['error']}", fg="red")
        elif d.get("changed"):
            typer.secho(f"CHANGED {d['file']}", fg="yellow")
            diff_text = d.get("diff", "")
            if diff_text:
                typer.echo(diff_text)
        else:
            typer.echo(f"UNCHANGED {d['file']}")


@audit_app.command("log")
def audit_log(limit: int = typer.Option(30, help="Number of entries")):
    """View audit trail."""
    from haip.operations.audit_release import AuditEngine

    ae = AuditEngine()
    entries = ae.list_audit_log(limit=limit)
    if not entries:
        typer.echo("No audit entries found.")
        return
    for e in entries:
        typer.echo(
            f"[{e.get('time_str', '')}] {e.get('action', ''):<12} "
            f"snap={e.get('snap_id', ''):<20} agent={e.get('agent', ''):<16} "
            f"{e.get('detail', '')}"
        )


@audit_app.command("rollback")
def audit_rollback(
    snap_id: str = typer.Argument(..., help="Snapshot ID to restore from"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Restore files from a snapshot."""
    from haip.operations.audit_release import AuditEngine

    ae = AuditEngine()

    diffs = ae.diff(snap_id)
    changed = [d for d in diffs if d.get("changed")]
    if not changed:
        typer.echo("No changes to roll back — files already match snapshot.")
        return

    typer.echo(f"Files to restore ({len(changed)}):")
    for d in changed:
        typer.echo(f"  {d['file']}")

    if not force:
        confirm = typer.confirm("Proceed with rollback?")
        if not confirm:
            typer.echo("Rollback cancelled.")
            return

    result = ae.rollback(snap_id)
    for p in result.get("restored", []):
        typer.echo(f"  RESTORED {p}")
    for p in result.get("errors", []):
        typer.secho(f"  ERROR {p}", fg="red")
    typer.echo(f"Done: {len(result.get('restored', []))} restored, "
               f"{len(result.get('errors', []))} errors.")
