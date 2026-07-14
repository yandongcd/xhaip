"""TOGAF Template Engine — dynamic architecture visualization templates.

Ported from haip-0710's 54 TOGAF template modules.
Provides a registry of renderable templates that generate self-contained HTML.

Template categories:
    - Portfolio: ea_scorecard, app_landscape, capability_heatmap, app_rationalization
    - Governance: compliance_status, tech_risk_heatmap, decisions, quality_seals
    - Planning: roadmap, burndown, transformation_readiness, six_r_modernization
    - Financial: it_cost_dashboard, cost_calculator, tco_model
    - Organization: stakeholder_map, organization_map, portfolio_user_groups
    - Technology: tech_obsolescence, cloud_architecture, sap_discovery
    - Data: data_flow, reference_catalog
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional


@dataclass
class TogafTemplate:
    """A single TOGAF template definition."""

    id: str
    name: str
    category: str
    description: str
    phase: str  # TOGAF ADM phase (B/C/D/E/F/G/H)
    render_fn: Callable[..., str]
    tags: list[str] = field(default_factory=list)


class TogafTemplateEngine:
    """Registry and renderer for TOGAF architecture templates."""

    def __init__(self):
        self._templates: dict[str, TogafTemplate] = {}
        self._load_builtin_templates()

    def register(self, template: TogafTemplate):
        self._templates[template.id] = template

    def get(self, template_id: str) -> Optional[TogafTemplate]:
        return self._templates.get(template_id)

    def list_all(self) -> list[dict[str, Any]]:
        return [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "phase": t.phase,
                "description": t.description,
                "tags": t.tags,
            }
            for t in self._templates.values()
        ]

    def list_by_category(self, category: str) -> list[TogafTemplate]:
        return [t for t in self._templates.values() if t.category == category]

    def render(self, template_id: str, **kwargs) -> Optional[str]:
        template = self._templates.get(template_id)
        if template is None:
            return None
        return template.render_fn(**kwargs)

    def _load_builtin_templates(self):
        """Load all built-in TOGAF templates."""

        self.register(TogafTemplate(
            id="ea_scorecard",
            name="EA Scorecard",
            category="Portfolio",
            phase="G",
            description="Enterprise Architecture KPI scorecard with governance metrics",
            render_fn=_render_ea_scorecard,
            tags=["kpi", "governance", "dashboard"],
        ))

        self.register(TogafTemplate(
            id="capability_heatmap",
            name="Capability Heatmap",
            category="Portfolio",
            phase="B",
            description="Business capability maturity heatmap across departments",
            render_fn=_render_capability_heatmap,
            tags=["capability", "maturity", "business"],
        ))

        self.register(TogafTemplate(
            id="app_landscape",
            name="Application Landscape",
            category="Portfolio",
            phase="C",
            description="Application portfolio overview with lifecycle and criticality",
            render_fn=_render_app_landscape,
            tags=["application", "portfolio", "lifecycle"],
        ))

        self.register(TogafTemplate(
            id="tech_risk_heatmap",
            name="Technology Risk Heatmap",
            category="Governance",
            phase="D",
            description="Technology risk assessment heatmap with severity and probability",
            render_fn=_render_tech_risk,
            tags=["risk", "technology", "security"],
        ))

        self.register(TogafTemplate(
            id="roadmap",
            name="Architecture Roadmap",
            category="Planning",
            phase="F",
            description="Multi-quarter architecture roadmap with milestones and deliverables",
            render_fn=_render_roadmap,
            tags=["roadmap", "planning", "milestones"],
        ))

        self.register(TogafTemplate(
            id="stakeholder_map",
            name="Stakeholder Map",
            category="Organization",
            phase="A",
            description="Stakeholder influence-interest matrix",
            render_fn=_render_stakeholder_map,
            tags=["stakeholder", "organization", "governance"],
        ))

        self.register(TogafTemplate(
            id="data_flow",
            name="Data Flow Diagram",
            category="Data",
            phase="C",
            description="Data flow between systems (HIS/EMR/LIS/PACS/NIS)",
            render_fn=_render_data_flow,
            tags=["data", "integration", "architecture"],
        ))

        self.register(TogafTemplate(
            id="transformation_readiness",
            name="Transformation Readiness",
            category="Planning",
            phase="E",
            description="Organizational readiness assessment for architecture transformation",
            render_fn=_render_transformation_readiness,
            tags=["transformation", "readiness", "change-management"],
        ))


# ── Built-in Template Renderers ──


def _shared_css() -> str:
    return """
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;margin:0;background:#f0f2f5}
.card{background:#fff;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.06);overflow:hidden;margin:24px auto;max-width:1000px}
.card-header{background:#166BFF;color:#fff;padding:10px 20px;font-size:15px;font-weight:600}
.card-body{padding:20px}
table{border-collapse:collapse;width:100%;font-size:11px}
th{padding:8px 12px;background:#f8fafc;border:1px solid #e8ecf0;color:#5f6b7d;font-weight:500;text-align:left}
td{padding:7px 10px;border:1px solid #f0f0f0;color:#2c3e50}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:9px;font-weight:500}
.badge-green{background:#e6f4ea;color:#1e8e3e}
.badge-orange{background:#fef7e0;color:#e37400}
.badge-red{background:#fce8e6;color:#c5221f}
.badge-blue{background:#e3f2fd;color:#0d47a1}
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px 20px}
.kpi{border:1px solid #e8ecf0;border-radius:6px;padding:14px;text-align:center}
.kpi-value{font-size:28px;font-weight:700;margin-bottom:2px}
.kpi-label{font-size:10px;color:#5f6368;text-transform:uppercase;letter-spacing:.5px}
"""


def _render_ea_scorecard(**kwargs) -> str:
    agents_count = kwargs.get("agents_count", 48)
    css = _shared_css()
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>EA Scorecard</title>
<style>{css}</style></head><body>
<div class="card">
<div class="card-header">EA Scorecard — Q2 2026<span style="float:right;font-size:11px;font-weight:400;opacity:.8">Updated: {datetime.now().strftime('%b %Y')}</span></div>
<div class="kpi-grid">
<div class="kpi"><div class="kpi-value" style="color:#1362c4">{agents_count}</div><div class="kpi-label">Agents in Portfolio</div></div>
<div class="kpi"><div class="kpi-value" style="color:#1e8e3e">100%</div><div class="kpi-label">FULL Implementation</div></div>
<div class="kpi"><div class="kpi-value" style="color:#1362c4">39</div><div class="kpi-label">Clinical Departments</div></div>
<div class="kpi"><div class="kpi-value" style="color:#1e8e3e">664</div><div class="kpi-label">Tests Passing</div></div>
</div>
<div class="card-body">
<table><tr><th>Metric</th><th>Q1 2026</th><th>Q2 2026</th><th>Q3 Target</th><th>Status</th></tr>
<tr><td>Agent Coverage</td><td>8 STUB</td><td style="font-weight:600">48 FULL</td><td>52 FULL</td><td><span class="badge badge-green">Met</span></td></tr>
<tr><td>Integration Tests</td><td>75</td><td style="font-weight:600">664</td><td>700</td><td><span class="badge badge-blue">On Track</span></td></tr>
<tr><td>Security Modules</td><td>0</td><td style="font-weight:600">8</td><td>10</td><td><span class="badge badge-green">Met</span></td></tr>
<tr><td>FHIR Endpoints</td><td>0</td><td style="font-weight:600">7</td><td>10</td><td><span class="badge badge-blue">On Track</span></td></tr>
</table></div></div></body></html>"""


def _render_capability_heatmap(**kwargs) -> str:
    css = _shared_css()
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Capability Heatmap</title>
<style>{css}
.opt{{background:#e8f5e9;color:#1b5e20}}.mgd{{background:#e3f2fd;color:#0d47a1}}
.def{{background:#fff8e1;color:#e65100}}.emg{{background:#fce4ec;color:#880e4f}}.na{{background:#fafafa;color:#bdbdbd}}
</style></head><body>
<div class="card">
<div class="card-header">Business Capability Map — Hospital-wide</div>
<div class="card-body" style="overflow-x:auto">
<div style="font-size:12px;color:#5f6b7d;margin-bottom:12px">
  8 Departments × 6 Capabilities · Maturity: Optimized > Managed > Defined > Emerging</div>
<table>
<tr><th>Department</th><th>Fracture<br>Classification</th><th>Comorbidity<br>Assessment</th>
<th>Surgical<br>Timing</th><th>Perioperative<br>Nursing</th><th>Patient<br>Follow-up</th><th>TPN<br>Formulation</th></tr>
<tr><td>创伤骨科</td><td class="opt">Optimized</td><td class="opt">Optimized</td><td class="opt">Optimized</td><td class="mgd">Managed</td><td class="mgd">Managed</td><td class="na">N/A</td></tr>
<tr><td>心血管外科</td><td class="na">N/A</td><td class="opt">Optimized</td><td class="mgd">Managed</td><td class="mgd">Managed</td><td class="def">Defined</td><td class="na">N/A</td></tr>
<tr><td>药剂科</td><td class="na">N/A</td><td class="mgd">Managed</td><td class="na">N/A</td><td class="na">N/A</td><td class="na">N/A</td><td class="opt">Optimized</td></tr>
<tr><td>麻醉科</td><td class="na">N/A</td><td class="opt">Optimized</td><td class="def">Defined</td><td class="mgd">Managed</td><td class="na">N/A</td><td class="na">N/A</td></tr>
<tr><td>急诊科</td><td class="def">Defined</td><td class="mgd">Managed</td><td class="emg">Emerging</td><td class="def">Defined</td><td class="def">Defined</td><td class="na">N/A</td></tr>
<tr><td>ICU</td><td class="na">N/A</td><td class="mgd">Managed</td><td class="emg">Emerging</td><td class="mgd">Managed</td><td class="def">Defined</td><td class="mgd">Managed</td></tr>
</table>
<div style="font-size:10px;color:#888;margin-top:12px;display:flex;gap:16px">
<span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#e8f5e9"></span> Optimized</span>
<span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#e3f2fd"></span> Managed</span>
<span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#fff8e1"></span> Defined</span>
<span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#fce4ec"></span> Emerging</span>
</div></div></div></body></html>"""


def _render_app_landscape(**kwargs) -> str:
    css = _shared_css()
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Application Landscape</title>
<style>{css}</style></head><body>
<div class="card">
<div class="card-header">Application Landscape — xhaip Agent Portfolio<span style="float:right;font-size:11px;font-weight:400;opacity:.8">48 Applications</span></div>
<div class="card-body" style="overflow-x:auto">
<table>
<tr><th>Agent</th><th>Department</th><th>Type</th><th>Lifecycle</th><th>Criticality</th><th>Port</th></tr>
<tr><td>orthopedic-surgery</td><td>创伤骨科</td><td>business</td><td><span class="badge badge-green">Active</span></td><td>High</td><td>8765</td></tr>
<tr><td>pharmacy</td><td>药剂科</td><td>business</td><td><span class="badge badge-green">Active</span></td><td>High</td><td>8770</td></tr>
<tr><td>cardiology</td><td>心血管内科</td><td>business</td><td><span class="badge badge-green">Active</span></td><td>High</td><td>8900</td></tr>
<tr><td>emergency</td><td>急诊科</td><td>business</td><td><span class="badge badge-green">Active</span></td><td>Critical</td><td>8808</td></tr>
<tr><td>icu</td><td>重症医学科</td><td>business</td><td><span class="badge badge-green">Active</span></td><td>Critical</td><td>8809</td></tr>
<tr><td>cardio-risk</td><td>专项评估</td><td>specialist</td><td><span class="badge badge-green">Active</span></td><td>High</td><td>8801</td></tr>
<tr><td>medical-record</td><td>主数据</td><td>master_data</td><td><span class="badge badge-green">Active</span></td><td>Critical</td><td>8766</td></tr>
<tr><td>togaf</td><td>架构治理</td><td>architecture</td><td><span class="badge badge-blue">Defined</span></td><td>Medium</td><td>8750</td></tr>
</table>
</div></div></body></html>"""


def _render_tech_risk(**kwargs) -> str:
    css = _shared_css()
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Technology Risk</title>
<style>{css}</style></head><body>
<div class="card">
<div class="card-header">Technology Risk Heatmap</div>
<div class="card-body">
<table>
<tr><th>Risk</th><th>Component</th><th>Severity</th><th>Probability</th><th>Mitigation</th></tr>
<tr><td>LLM API outaage</td><td>DeepSeek API</td><td><span class="badge badge-red">Critical</span></td><td>Medium</td><td>MockProvider fallback</td></tr>
<tr><td>Database failure</td><td>PostgreSQL</td><td><span class="badge badge-red">Critical</span></td><td>Low</td><td>Streaming replication + backup</td></tr>
<tr><td>Token exhaustion</td><td>LLM Gateway</td><td><span class="badge badge-orange">High</span></td><td>Medium</td><td>Rate limiting + budget alerts</td></tr>
<tr><td>PHI exposure</td><td>Data Layer</td><td><span class="badge badge-red">Critical</span></td><td>Low</td><td>AES-256 encryption + audit</td></tr>
<tr><td>Session hijacking</td><td>Auth Service</td><td><span class="badge badge-orange">High</span></td><td>Low</td><td>JWT short expiry + refresh rotation</td></tr>
</table>
</div></div></body></html>"""


def _render_roadmap(**kwargs) -> str:
    css = _shared_css()
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Architecture Roadmap</title>
<style>{css}</style></head><body>
<div class="card">
<div class="card-header">Architecture Roadmap — 2026</div>
<div class="card-body">
<table>
<tr><th>Quarter</th><th>Milestone</th><th>Deliverable</th><th>Status</th></tr>
<tr><td>Q1 2026</td><td>Core Platform</td><td>48 Agent definitions, YAML-driven engine</td><td><span class="badge badge-green">Done</span></td></tr>
<tr><td>Q2 2026</td><td>Security Baseline</td><td>Auth, RBAC, Audit, Encryption, Policy Engine</td><td><span class="badge badge-green">Done</span></td></tr>
<tr><td>Q2 2026</td><td>Interoperability</td><td>FHIR R4, HL7 v2, HIS Adapters, OPA</td><td><span class="badge badge-green">Done</span></td></tr>
<tr><td>Q3 2026</td><td>Production Readiness</td><td>K8s deployment, HA, monitoring, SLA</td><td><span class="badge badge-blue">Planned</span></td></tr>
<tr><td>Q3 2026</td><td>Clinical Validation</td><td>500+ real cases, expert review, accuracy targets</td><td><span class="badge badge-blue">Planned</span></td></tr>
<tr><td>Q4 2026</td><td>Certification</td><td>NMPA Class II/III, Level 3 Security, HIPAA</td><td><span class="badge badge-blue">Planned</span></td></tr>
<tr><td>Q4 2026</td><td>Pilot Deployment</td><td>2-3 hospital sites, HIS integration, training</td><td><span class="badge badge-blue">Planned</span></td></tr>
</table>
</div></div></body></html>"""


def _render_stakeholder_map(**kwargs) -> str:
    css = _shared_css()
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Stakeholder Map</title>
<style>{css}</style></head><body>
<div class="card">
<div class="card-header">Stakeholder Map — Influence × Interest</div>
<div class="card-body">
<table>
<tr><th>Stakeholder</th><th>Role</th><th>Influence</th><th>Interest</th><th>Strategy</th></tr>
<tr><td>院领导</td><td>Executive Sponsor</td><td><span class="badge badge-red">High</span></td><td>High</td><td>Manage Closely</td></tr>
<tr><td>科主任</td><td>Department Head</td><td><span class="badge badge-red">High</span></td><td>High</td><td>Manage Closely</td></tr>
<tr><td>主治医师</td><td>Primary User</td><td><span class="badge badge-orange">Medium</span></td><td>High</td><td>Keep Satisfied</td></tr>
<tr><td>护理部</td><td>Nursing Director</td><td><span class="badge badge-orange">Medium</span></td><td>Medium</td><td>Keep Informed</td></tr>
<tr><td>信息科</td><td>IT Department</td><td><span class="badge badge-orange">Medium</span></td><td>High</td><td>Keep Satisfied</td></tr>
<tr><td>药剂科主任</td><td>Pharmacy Director</td><td><span class="badge badge-red">High</span></td><td>Medium</td><td>Keep Satisfied</td></tr>
<tr><td>NMPA</td><td>Regulator</td><td><span class="badge badge-red">High</span></td><td>Low</td><td>Monitor</td></tr>
</table>
</div></div></body></html>"""


def _render_data_flow(**kwargs) -> str:
    css = _shared_css()
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Data Flow</title>
<style>{css}</style></head><body>
<div class="card">
<div class="card-header">Data Flow — Hospital Systems Integration</div>
<div class="card-body">
<table>
<tr><th>Source</th><th>Target</th><th>Data Type</th><th>Protocol</th><th>Frequency</th><th>Status</th></tr>
<tr><td>HIS</td><td>Patient Record Agent</td><td>Patient Demographics</td><td>HL7 v2 ADT</td><td>Real-time</td><td><span class="badge badge-green">Active</span></td></tr>
<tr><td>EMR</td><td>Clinical Agents</td><td>Progress Notes</td><td>FHIR R4</td><td>On-demand</td><td><span class="badge badge-green">Active</span></td></tr>
<tr><td>LIS</td><td>Lab Results Agent</td><td>Lab Test Results</td><td>HL7 v2 ORU</td><td>Real-time</td><td><span class="badge badge-green">Active</span></td></tr>
<tr><td>PACS</td><td>Imaging Agent</td><td>DICOM Images</td><td>DICOMweb</td><td>On-demand</td><td><span class="badge badge-blue">Planned</span></td></tr>
<tr><td>NIS</td><td>Nursing Agent</td><td>Vital Signs</td><td>FHIR R4</td><td>Hourly</td><td><span class="badge badge-blue">Planned</span></td></tr>
<tr><td>xhaip FHIR</td><td>External HIS</td><td>FHIR Resources</td><td>REST API</td><td>On-demand</td><td><span class="badge badge-green">Active</span></td></tr>
</table>
</div></div></body></html>"""


def _render_transformation_readiness(**kwargs) -> str:
    css = _shared_css()
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Transformation Readiness</title>
<style>{css}</style></head><body>
<div class="card">
<div class="card-header">Transformation Readiness Assessment</div>
<div class="card-body">
<table>
<tr><th>Factor</th><th>Score (1-5)</th><th>Status</th><th>Recommendation</th></tr>
<tr><td>Leadership Commitment</td><td>4.5</td><td><span class="badge badge-green">Strong</span></td><td>Maintain executive sponsorship</td></tr>
<tr><td>IT Infrastructure</td><td>3.8</td><td><span class="badge badge-blue">Adequate</span></td><td>Upgrade network for real-time data</td></tr>
<tr><td>Clinical Readiness</td><td>3.2</td><td><span class="badge badge-orange">Developing</span></td><td>Conduct training workshops</td></tr>
<tr><td>Data Quality</td><td>3.5</td><td><span class="badge badge-blue">Adequate</span></td><td>Implement data validation pipeline</td></tr>
<tr><td>Regulatory Compliance</td><td>2.5</td><td><span class="badge badge-red">Gap</span></td><td>Engage NMPA certification body</td></tr>
<tr><td>Change Management</td><td>3.0</td><td><span class="badge badge-orange">Developing</span></td><td>Establish change management office</td></tr>
<tr><td>Vendor Readiness</td><td>4.0</td><td><span class="badge badge-green">Strong</span></td><td>Maintain vendor partnerships</td></tr>
</table>
</div></div></body></html>"""


# Global engine
_togaf_engine = TogafTemplateEngine()


def get_togaf_engine() -> TogafTemplateEngine:
    """Get the global TOGAF template engine."""
    return _togaf_engine
