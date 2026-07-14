"""LeanIX Factsheet Exporter — enterprise architecture factsheet generation.

Ported from haip-0710's NX domain LeanIX integration.
Generates standardized fact sheets for:
    - Application (agent service)
    - Interface (A2A relationships)
    - Business Capability (clinical capabilities)
    - Data Object (data entities)
    - IT Component (infrastructure)

Compatible with LeanIX SaaS import format.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FactSheet:
    """A single LeanIX fact sheet."""

    id: str
    type: str  # Application, Interface, BusinessCapability, DataObject, ITComponent
    name: str
    display_name: str = ""
    description: str = ""
    status: str = "active"
    tags: list[str] = field(default_factory=list)
    relations: list[dict[str, str]] = field(default_factory=list)
    fields: dict[str, Any] = field(default_factory=dict)


class LeanIXExporter:
    """Generates LeanIX-compatible fact sheets from xhaip metadata."""

    def __init__(self):
        self._facts: dict[str, FactSheet] = {}

    def add_application(
        self,
        app_id: str,
        name: str,
        display_name: str = "",
        description: str = "",
        owner: str = "",
        lifecycle: str = "active",
        criticality: str = "medium",
        **extra,
    ):
        """Add an Application fact sheet (maps to xhaip agent)."""
        fs = FactSheet(
            id=app_id,
            type="Application",
            name=name,
            display_name=display_name or name,
            description=description,
            status=lifecycle,
            fields={
                "owner": owner,
                "lifecycle": lifecycle,
                "criticality": criticality,
                "category": extra.get("category", "Clinical AI Agent"),
                **extra,
            },
        )
        self._facts[app_id] = fs
        return fs

    def add_interface(
        self,
        interface_id: str,
        name: str,
        source_app: str,
        target_app: str,
        protocol: str = "A2A",
        frequency: str = "on-demand",
    ):
        """Add an Interface fact sheet (maps to A2A tools)."""
        fs = FactSheet(
            id=interface_id,
            type="Interface",
            name=name,
            description=f"Agent-to-Agent call: {source_app} → {target_app}",
            fields={
                "source": source_app,
                "target": target_app,
                "protocol": protocol,
                "frequency": frequency,
            },
        )
        self._facts[interface_id] = fs
        # Add relation
        if source_app in self._facts:
            self._facts[source_app].relations.append({
                "target": interface_id,
                "type": "providesInterface",
            })
        if target_app in self._facts:
            self._facts[target_app].relations.append({
                "target": interface_id,
                "type": "consumesInterface",
            })
        return fs

    def add_business_capability(
        self,
        cap_id: str,
        name: str,
        description: str = "",
        owner: str = "",
    ):
        """Add a Business Capability fact sheet."""
        fs = FactSheet(
            id=cap_id,
            type="BusinessCapability",
            name=name,
            description=description,
            fields={"owner": owner},
        )
        self._facts[cap_id] = fs
        return fs

    def add_data_object(
        self,
        obj_id: str,
        name: str,
        description: str = "",
        classification: str = "internal",
    ):
        """Add a Data Object fact sheet."""
        fs = FactSheet(
            id=obj_id,
            type="DataObject",
            name=name,
            description=description,
            fields={"classification": classification},
        )
        self._facts[obj_id] = fs
        return fs

    def add_it_component(
        self,
        comp_id: str,
        name: str,
        technology: str = "",
        version: str = "",
        lifecycle: str = "active",
    ):
        """Add an IT Component fact sheet."""
        fs = FactSheet(
            id=comp_id,
            type="ITComponent",
            name=name,
            description=f"{technology} {version}",
            fields={"technology": technology, "version": version, "lifecycle": lifecycle},
        )
        self._facts[comp_id] = fs
        return fs

    # ── Auto-discovery ──

    def auto_discover_from_registry(self):
        """Auto-generate fact sheets from the xhaip agent registry."""
        from haip.agent import list_all

        agents = list_all()

        for name, plugin in agents.items():
            # Application fact sheet
            self.add_application(
                app_id=f"app-{name}",
                name=name,
                display_name=plugin.cn_name,
                description=f"{plugin.department} — {plugin.type} agent",
                owner=plugin.department,
                category=plugin.type,
                version=plugin.version,
            )

            # Interface fact sheets (dependencies)
            for dep in plugin.depends_on:
                dep_agent = dep.get("agent", "")
                if dep_agent:
                    self.add_interface(
                        interface_id=f"if-{name}-{dep_agent}",
                        name=f"{name}→{dep_agent}",
                        source_app=name,
                        target_app=dep_agent,
                    )

            # Tool interfaces
            for tool in plugin.tools:
                self.add_interface(
                    interface_id=f"if-{name}-{tool.name}",
                    name=f"{name}:{tool.name}",
                    source_app="portal",
                    target_app=name,
                    protocol="REST",
                    frequency="on-demand",
                )

        # IT Components
        self.add_it_component("it-postgres", "PostgreSQL", "PostgreSQL", "16", "active")
        self.add_it_component("it-redis", "Redis", "Redis", "7", "active")
        self.add_it_component("it-fastapi", "FastAPI", "Python FastAPI", "0.100+", "active")
        self.add_it_component("it-deepseek", "DeepSeek API", "LLM API", "deepseek-chat", "active")
        self.add_it_component("it-kubernetes", "Kubernetes", "K8s", "1.29", "active")

        # Data Objects
        for name in ["Patient", "LabResult", "Medication", "Diagnosis", "Procedure"]:
            self.add_data_object(
                f"data-{name.lower()}",
                name,
                f"Core clinical data entity: {name}",
            )

        # Business Capabilities
        capabilities = [
            ("bc-fracture-classification", "骨折分型", "AI-assisted fracture classification"),
            ("bc-anticoagulation", "抗凝管理", "Perioperative anticoagulation management"),
            ("bc-tpn-compounding", "TPN 配制", "Total Parenteral Nutrition compounding"),
            ("bc-prescription-review", "处方审核", "AI-powered prescription review"),
            ("bc-anesthesia-risk", "麻醉风险评估", "Pre-anesthesia risk assessment"),
            ("bc-cardio-risk", "心血管风险评估", "Cardiac risk assessment"),
            ("bc-mdt-coordination", "MDT 会诊协调", "Multi-disciplinary team coordination"),
        ]
        for cap_id, name, desc in capabilities:
            self.add_business_capability(cap_id, name, desc)

    # ── Export ──

    def to_leanix_json(self) -> dict[str, Any]:
        """Export all fact sheets in LeanIX-compatible JSON format."""
        export_date = datetime.now().isoformat()

        factsheets = []
        for fs_id, fs in self._facts.items():
            factsheets.append({
                "id": fs.id,
                "type": fs.type,
                "name": fs.name,
                "displayName": fs.display_name,
                "description": fs.description,
                "status": fs.status,
                "tags": [{"name": t} for t in fs.tags],
                "relations": fs.relations,
                "fields": [
                    {"key": k, "value": v} for k, v in fs.fields.items()
                ],
            })

        return {
            "metadata": {
                "exportDate": export_date,
                "sourceSystem": "xhaip",
                "leanixVersion": "4.0",
                "totalFactSheets": len(factsheets),
            },
            "factSheets": factsheets,
        }

    def to_json(self, indent: int = 2) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_leanix_json(), ensure_ascii=False, indent=indent)

    def to_html_summary(self) -> str:
        """Generate an HTML summary of all fact sheets."""
        facts = self._facts
        by_type: dict[str, list[FactSheet]] = {}
        for fs in facts.values():
            by_type.setdefault(fs.type, []).append(fs)

        rows = ""
        for ftype, fsheets in sorted(by_type.items()):
            rows += f'<tr><td colspan="4"><strong>{ftype}</strong> ({len(fsheets)})</td></tr>'
            for fs in sorted(fsheets, key=lambda f: f.name):
                rows += (
                    f'<tr><td>{fs.display_name}</td>'
                    f'<td>{fs.id}</td>'
                    f'<td>{fs.description[:80]}</td>'
                    f'<td>{fs.status}</td></tr>'
                )

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>xhaip LeanIX FactSheets</title>
<style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f5f5f5; }}
    tr:nth-child(even) {{ background: #fafafa; }}
</style></head>
<body>
<h1>xhaip LeanIX FactSheets</h1>
<p>Total: {len(facts)} fact sheets | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<table>
<tr><th>Name</th><th>ID</th><th>Description</th><th>Status</th></tr>
{rows}
</table>
</body></html>"""


# Global singleton
_exporter = LeanIXExporter()


def get_leanix_exporter() -> LeanIXExporter:
    """Get the global LeanIX exporter singleton."""
    return _exporter


def auto_discover() -> LeanIXExporter:
    """Run auto-discovery and return the exporter."""
    _exporter.auto_discover_from_registry()
    return _exporter
