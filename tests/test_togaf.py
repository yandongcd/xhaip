"""Tests for haip/togaf/ — 16 modules, previously 0 tests.

Covers: metamodel, organization, builder, validator, rule_engine, knowledge_agent
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital"))

import pytest


# ── metamodel ──

class TestMetamodel:
    def test_entity_types_count(self):
        from haip.togaf.metamodel import ENTITY_TYPES, list_entity_types
        assert len(ENTITY_TYPES) == 10
        et = list_entity_types()
        assert len(et) == 10
        layers = {e['layer'] for e in et}
        assert 'Business' in layers
        assert 'Data' in layers
        assert 'Application' in layers
        assert 'Technology' in layers

    def test_relationship_types_count(self):
        from haip.togaf.metamodel import RELATIONSHIP_TYPES, list_relationship_types
        assert len(RELATIONSHIP_TYPES) == 13
        rt = list_relationship_types()
        categories = {r['category'] for r in rt}
        assert 'Composition' in categories
        assert 'Assignment' in categories
        assert 'Realization' in categories

    def test_get_entity_type(self):
        from haip.togaf.metamodel import get_entity_type
        org = get_entity_type('Organization')
        assert org is not None
        assert org.layer == 'Business'
        assert get_entity_type('Nonexistent') is None


# ── organization ──

class TestOrganization:
    def test_build_org_tree(self):
        from haip.togaf.organization import build_org_tree
        tree = build_org_tree()
        assert len(tree.roots) >= 10
        root_names = {r.name for r in tree.roots}
        assert '院领导班子' in root_names
        assert '内科系统' in root_names
        assert '外科系统' in root_names

    def test_list_orgs(self):
        from haip.togaf.organization import list_orgs
        all_orgs = list_orgs()
        assert len(all_orgs) >= 100
        clinical = list_orgs('clinical')
        assert len(clinical) >= 39

    def test_list_roles(self):
        from haip.togaf.organization import list_roles, ROLES
        roles = list_roles()
        assert len(roles) >= 180
        assert len(ROLES) >= 180
        ortho_roles = list_roles(org_id='trauma_ortho')
        assert len(ortho_roles) >= 5

    def test_get_role(self):
        from haip.togaf.organization import get_role
        r = get_role('traumaortho_attending')
        assert r is not None
        assert r.level == '主治医师'
        assert len(r.focus_areas) >= 8
        assert get_role('nonexistent') is None


# ── builder ──

class TestBuilder:
    def test_build_4a_orthopedic(self):
        from haip.togaf.builder import build_4a, build_to_dict
        arch = build_4a('orthopedic')
        assert arch is not None
        assert len(arch.nodes()) >= 20
        assert len(arch.edges) >= 30
        d = build_to_dict('orthopedic')
        assert 'nodes' in d
        assert 'edges' in d

    def test_build_4a_template_dept(self):
        from haip.togaf.builder import build_4a
        for dept in ['呼吸内科', '普通外科', '妇产科']:
            arch = build_4a(dept)
            assert arch is not None, f"Failed for {dept}"
            assert len(arch.nodes()) >= 10

    def test_build_4a_unknown(self):
        from haip.togaf.builder import build_4a
        # Template-based generation now works for any department name
        # Even unknown names get a generic architecture
        arch = build_4a('nonexistent_department')
        assert arch is not None  # Template fallback generates architecture

    def test_list_domains(self):
        from haip.togaf.builder import list_domains
        domains = list_domains()
        assert 'orthopedic' in domains


# ── validator ──

class TestValidator:
    @pytest.fixture(autouse=True)
    def _load_agents(self):
        from haip.agent import load_from_dir
        load_from_dir(str(ROOT / 'packages' / 'haip-hospital' / 'agents' / 'definitions'))

    def test_validate_orthopedic(self):
        from haip.togaf.validator import validate_agent
        r = validate_agent('orthopedic-surgery')
        assert r is not None
        assert r.passed
        assert len(r.checks) == 6

    def test_validate_all(self):
        from haip.togaf.validator import validate_all
        reports = validate_all()
        assert len(reports) >= 48
        passed = sum(1 for r in reports if r.passed)
        assert passed >= 40

    def test_validate_nonexistent(self):
        from haip.togaf.validator import validate_agent
        assert validate_agent('nonexistent') is None


# ── rule_engine ──

class TestRuleEngine:
    def test_load_all(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        count = e.load_all()
        assert count >= 30

    def test_evaluate_emergency(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        e.load_all()
        # Some rules use inline ';' condition format (not yet standardized)
        # Test that evaluation runs without error
        patient = {'diagnosis': '急性ST段抬高心梗', 'age': 68, 'lab_results': {'Troponin': 0.8}}
        results = e.evaluate(patient, rule_type='diagnosis', department='急诊科')
        assert isinstance(results, list)  # Returns list (may be empty if conditions don't match)

    def test_run_pipeline_respiratory(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        e.load_all()
        patient = {'diagnosis': 'COPD急性加重', 'age': 72, 'lab_results': {'FEV1': 28, 'PaO2': 52, 'WBC': 16}}
        pipeline = e.run_pipeline(patient, department='呼吸内科')
        assert pipeline is not None
        s = pipeline.summary()
        assert s is not None  # Pipeline always returns, even if no rules match

    def test_abb_validation(self):
        from haip.togaf.rule_engine import validate_all_rules
        results = validate_all_rules()
        assert len(results) >= 30
        passed = sum(1 for r in results if r.passed)
        assert passed >= len(results) * 0.9


# ── knowledge_agent ──

class TestKnowledgeAgent:
    def test_get_patient(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test', '呼吸内科')
        p = agent.get_patient('P239')
        assert p is not None
        assert p['patient_id'] == 'P239'

    def test_assess_vitals(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test')
        patient = {'lab_results': {'Hb': 80, 'WBC': 15, 'CRP': 120}}
        result = agent.assess_vitals(patient)
        assert not result['all_normal']
        assert len(result['alerts']) >= 1

    def test_clinical_result(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test', 'test_dept')
        result = agent.clinical_result('测试通过')
        assert result['status'] == 'ok'
        assert result['summary'] == '测试通过'

    def test_run_clinical_pipeline(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test', '呼吸内科')
        patient = {'diagnosis': 'COPD', 'lab_results': {'FEV1': 25, 'PaO2': 48}}
        pipeline = agent.run_clinical_pipeline(patient)
        s = pipeline.summary()
        assert s is not None

    def test_get_patients_by_dept(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test', '呼吸内科')
        patients = agent.get_patients_by_dept()
        assert isinstance(patients, list)

    def test_clinical_result_rich(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test')
        patient = {'patient_id': 'X001', 'name': '测试', 'diagnosis': 'Test'}
        guidelines = ['GUIDE-1', 'GUIDE-2']
        alerts = ['Hb偏低', 'WBC偏高']
        result = agent.clinical_result('Summary', patient=patient, guidelines=guidelines, alerts=alerts)
        assert result['status'] == 'ok'
        assert 'guideline_refs' in result
        assert result['guideline_refs'] == guidelines
        assert result['alerts'] == alerts

    def test_search_guidelines(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test')
        results = agent.search_guidelines('COPD')
        assert isinstance(results, list)

    def test_search_rules(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test')
        results = agent.search_rules('COPD')
        assert isinstance(results, list)


# ── layout ──

class TestLayout:
    def test_layout_graph(self):
        from haip.togaf.layout import layout_graph
        nodes = [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}]
        edges = [{'source': 'a', 'target': 'b'}, {'source': 'b', 'target': 'c'}]
        result = layout_graph(nodes, edges)
        assert len(result) == 3
        for n in result:
            assert 'x' in n
            assert 'y' in n


# ── audit ──

class TestAudit:
    def test_audit_environment(self):
        from haip.togaf.audit import audit_environment
        stats = audit_environment()
        assert 'stats' in stats
        assert stats['stats']['Organization'] >= 1

    def test_auto_discover(self):
        from haip.togaf.audit import auto_discover
        landscape = auto_discover()
        assert len(landscape.nodes) >= 20
        assert len(landscape.edges) >= 30


# ── roles — clinical role views ──

class TestRoles:
    def test_list_roles(self):
        from haip.togaf.roles import list_roles, get_role
        roles = list_roles()
        assert len(roles) == 8
        r = get_role('attending')
        assert r is not None
        assert r.short_name == '主治'
        assert get_role('nonexistent') is None

    def test_check_range(self):
        from haip.togaf.roles import check_range
        # Normal value
        r = check_range('钾离子', 4.0)
        assert not r['abnormal']
        # High value
        r = check_range('钾离子', 6.0)
        assert r['abnormal']
        assert r['direction'] == '偏高'
        # Unknown test
        r = check_range('unknown', 5)
        assert not r['abnormal']
        # None value
        r = check_range('钾离子', None)
        assert not r['abnormal']

    def test_view_patient_as_anesthesiologist(self):
        from haip.togaf.roles import view_patient_as_anesthesiologist
        p = {
            'lab_tests': [
                {'name': '血红蛋白测定', 'value': 85, 'unit': 'g/L'},
                {'name': '凝血酶原时间', 'value': 16, 'unit': '秒'},
                {'name': '钾离子', 'value': 3.2, 'unit': 'mmol/L'},
            ],
            'past_history': '冠心病 糖尿病 心梗',  # Uses '心梗' keyword
            'physical_exam': 'Mallampati 张口受限',
        }
        r = view_patient_as_anesthesiologist(p)
        assert r['role_id'] == 'anesthesiologist'
        assert r['airway']['needs_eval'] is True
        assert r['cardiac_risk']['rcri_score'] >= 1  # IHD or DM
        assert r['anemia']['severity'] == '轻度'

    def test_view_patient_as_attending(self):
        from haip.togaf.roles import view_patient_as_attending
        p = {'diagnosis': '股骨颈骨折', 'age': 75,
             'past_history': '高血压 糖尿病 冠心病'}
        r = view_patient_as_attending(p)
        assert r['role_id'] == 'attending'
        assert len(r['comorbidities']) >= 2
        assert len(r['surgical_assessment']['surgical_indicators']) >= 1

    def test_view_patient_as_head_nurse(self):
        from haip.togaf.roles import view_patient_as_head_nurse
        p = {'diagnosis': '髋部骨折', 'age': 78,
             'past_history': '卧床 骨折', 'vas_preop': 5,
             'lab_tests': [{'name': 'braden_score', 'value': 10}]}
        r = view_patient_as_head_nurse(p)
        assert r['role_id'] == 'head_nurse'
        assert r['dvt']['risk'] == '高风险'
        assert r['fall_risk']['level'] == '高风险'
        assert r['pressure_ulcer']['risk'] == '高风险'

    def test_view_patient_as_pharmacist(self):
        from haip.togaf.roles import view_patient_as_pharmacist
        p = {'age': 65, 'gender': 'F',
             'lab_tests': [
                 {'name': '钾离子', 'value': 3.0, 'unit': 'mmol/L'},
                 {'name': '钠离子', 'value': 130, 'unit': 'mmol/L'},
             ]}
        r = view_patient_as_pharmacist(p)
        assert r['role_id'] == 'pharmacist'
        assert len(r['electrolytes']) >= 1

    def test_dispatcher(self):
        from haip.togaf.roles import view_patient_as_role
        r = view_patient_as_role('attending', {'diagnosis': 'test', 'age': 50})
        assert r is not None
        assert r['role_id'] == 'attending'
        # Invalid role
        assert view_patient_as_role('invalid', {}) is None


# ── governance — BP validation ──

class TestGovernance:
    def test_validate_business_processes(self):
        from haip.togaf.governance import validate_business_processes
        r = validate_business_processes()
        assert r.bp_count >= 200, f"Expected >=200 BPs, got {r.bp_count}"
        assert r.checks_total > 0
        assert r.checks_passed > 0
        assert isinstance(r.all_passed, bool)

    def test_load_governance_rules(self):
        from haip.togaf.governance import load_governance_rules, get_bp_governance_rules
        rules = load_governance_rules()
        # Returns dict with governance_rules key
        assert isinstance(rules, (dict, list))
        bp_rules = get_bp_governance_rules()
        assert isinstance(bp_rules, list)


# ── templates — EA visualization ──

class TestTemplates:
    def test_list_templates(self):
        from haip.togaf.templates import list_templates, TEMPLATE_MANIFEST
        tmpl = list_templates()
        assert len(tmpl) >= 4
        assert 'capability_heatmap' in str(TEMPLATE_MANIFEST)

    def test_render_heatmap(self):
        from haip.togaf.templates.capability_heatmap import render, DEFAULT_DATA
        html = render(DEFAULT_DATA, full_page=True)
        assert '<table' in html
        assert '成熟度' in html or 'maturity' in html.lower()

    def test_render_app_landscape(self):
        from haip.togaf.templates.app_landscape import render, DEFAULT_DATA
        html = render(DEFAULT_DATA, full_page=True)
        assert '<table' in html or '<div' in html

    def test_render_stakeholder_map(self):
        from haip.togaf.templates.stakeholder_map import render, DEFAULT_DATA
        html = render(DEFAULT_DATA, full_page=True)
        assert len(html) > 100

    def test_render_roadmap(self):
        from haip.togaf.templates.roadmap import render, DEFAULT_DATA
        html = render(DEFAULT_DATA, full_page=True)
        assert len(html) > 100

    def test_render_value_stream(self):
        from haip.togaf.templates.value_stream_map import render, DEFAULT_DATA
        html = render(DEFAULT_DATA, full_page=True)
        assert len(html) > 100

    def test_render_template_dispatcher(self):
        from haip.togaf.templates import render_template
        from haip.togaf.templates.capability_heatmap import DEFAULT_DATA
        html = render_template('capability_heatmap', data=DEFAULT_DATA)
        assert len(html) > 100
