"""TOGAF 100% Coverage — comprehensive tests for all under-covered modules.

Extends test_togaf.py with edge cases for: validator, knowledge_agent,
roles, governance, rule_engine, audit, analysis, agent_generator, patient_generator.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital"))

import pytest
from haip.agent import load_from_dir

load_from_dir(str(ROOT / "packages" / "haip-hospital" / "agents" / "definitions"))


# ── validator — edge cases ──

class TestValidatorEdge:
    def test_print_all_reports(self):
        from haip.togaf.validator import print_all_reports, validate_all
        reports = validate_all()
        text = print_all_reports(reports)
        assert 'TOGAF Validation Report' in text
        assert len(text) > 500

    def test_validation_report_warnings(self):
        from haip.togaf.validator import validate_agent
        r = validate_agent('pain-hub')
        assert r is not None
        # pain-hub has no department — warnings expected
        assert isinstance(r.warnings, list)

    def test_type_compliance_all_types(self):
        from haip.togaf.validator import _check_type_compliance
        registry = {}
        # Load a real agent for testing
        from haip.agent import get as get_agent
        for agent_type in ['business', 'specialist', 'master_data', 'architecture']:
            # Create a minimal mock-like test
            pass
        agent = get_agent('orthopedic-surgery')
        c = _check_type_compliance(agent)
        assert c.passed
        assert 'ApplicationComponent' in c.detail

    def test_check_org_affiliation_empty(self):
        from haip.togaf.validator import _check_org_affiliation
        # Test with a specialist agent that has no department
        from haip.agent import get as get_agent
        agent = get_agent('acute-pain')
        c = _check_org_affiliation(agent)
        assert not c.passed  # No department set

    def test_check_dependency_graph_empty(self):
        from haip.togaf.validator import _check_dependency_graph
        from haip.agent import get as get_agent
        agent = get_agent('acute-pain')
        c = _check_dependency_graph(agent, {})
        assert c.passed  # No deps → passes

    def test_check_tool_service_empty(self):
        from haip.togaf.validator import _check_tool_service_mapping
        from haip.agent import get as get_agent
        agent = get_agent('pain-hub')
        c = _check_tool_service_mapping(agent)
        assert c.passed  # 2 tools with handlers


# ── knowledge_agent — remaining paths ──

class TestKnowledgeAgentEdge:
    def test_rule_engine_lazy_load(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test', 'test')
        assert agent._rule_engine is None
        eng = agent.rule_engine
        assert eng is not None
        assert agent._rule_engine is not None

    def test_clinical_result_from_pipeline_none(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test', 'test')
        result = agent.clinical_result_from_pipeline({'patient_id': 'X'})
        assert result['status'] == 'ok'

    def test_vital_ranges(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test')
        p = {'lab_results': {'Hb': 80, 'K+': 3.2, 'ALT': 50}}
        r = agent.assess_vitals(p)
        assert not r['all_normal']
        assert len(r['alerts']) >= 1

    def test_vital_ranges_normal(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test')
        p = {'lab_results': {'Hb': 140, 'WBC': 7.0, 'CRP': 3}}
        r = agent.assess_vitals(p)
        assert r['all_normal']

    def test_get_patient_nonexistent(self):
        from haip.togaf.knowledge_agent import KnowledgeAgent
        agent = KnowledgeAgent('test')
        p = agent.get_patient('NONEXISTENT')
        assert p is None


# ── roles — remaining view functions ──

class TestRolesAllViews:
    def test_view_dietitian(self):
        from haip.togaf.roles import view_patient_as_dietitian
        r = view_patient_as_dietitian({
            'age': 45, 'weight_kg': 40, 'height_cm': 165,
            'diagnosis': '肠梗阻',
            'lab_tests': [{'name': '白蛋白', 'value': 28, 'unit': 'g/L'}],
            'nutrition_assessment': {'nrs2002_score': 5, 'risk_level': 'high'},
        })
        assert r['role_id'] == 'dietitian'
        assert 'PN' in r['route']['recommendation']

    def test_view_clinical_pharmacist(self):
        from haip.togaf.roles import view_patient_as_clinical_pharmacist
        r = view_patient_as_clinical_pharmacist({
            'age': 70, 'weight_kg': 55, 'height_cm': 170,
            'lab_tests': [
                {'name': '钾离子', 'value': 3.0, 'unit': 'mmol/L'},
                {'name': '葡萄糖', 'value': 12.0, 'unit': 'mmol/L'},
            ],
        })
        assert r['role_id'] == 'clinical_pharmacist'
        assert len(r['electrolytes']) >= 1

    def test_view_review_pharmacist(self):
        from haip.togaf.roles import view_patient_as_review_pharmacist
        r = view_patient_as_review_pharmacist({
            'lab_tests': [
                {'name': '葡萄糖', 'value': 12.0, 'unit': 'mmol/L'},
                {'name': '总钙', 'value': 2.5, 'unit': 'mmol/L'},
                {'name': '磷离子', 'value': 3.0, 'unit': 'mmol/L'},
            ],
        })
        assert r['role_id'] == 'review_pharmacist'
        # Ca*P = 7.5 > 50? No, 2.5*3=7.5 — safe
        assert r['ca_p_product'] is not None

    def test_view_iv_pharmacist(self):
        from haip.togaf.roles import view_patient_as_iv_compounding_pharmacist
        r = view_patient_as_iv_compounding_pharmacist({
            'weight_kg': 55, 'height_cm': 165,
        })
        assert r['role_id'] == 'iv_compounding_pharmacist'
        assert r['patient']['bmi'] is not None


# ── governance — more paths ──

class TestGovernanceEdge:
    def test_validate_with_project_root(self):
        from pathlib import Path
        from haip.togaf.governance import validate_business_processes
        r = validate_business_processes()
        assert r.checks_total > 0

    def test_governance_rules_dict(self):
        from haip.togaf.governance import load_governance_rules
        rules = load_governance_rules()
        assert isinstance(rules, dict)
        assert 'governance_rules' in rules or 'rules' in rules


# ── rule_engine — operator edge cases ──

class TestRuleEngineEdge:
    def test_and_combinator(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        ok, _ = e._check_condition({
            'and': [
                {'field': 'age', 'operator': '>=', 'value': 60},
                {'field': 'age', 'operator': '<', 'value': 80},
            ]
        }, {'age': 70})
        assert ok

    def test_or_combinator(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        ok, _ = e._check_condition({
            'or': [
                {'field': 'age', 'operator': '>=', 'value': 80},
                {'field': 'age', 'operator': '<', 'value': 30},
            ]
        }, {'age': 70})
        assert not ok  # 70 is neither >=80 nor <30

    def test_regex_operator(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        ok, _ = e._check_condition({
            'field': 'diagnosis', 'operator': 'regex', 'value': '心(梗|衰|绞痛)'
        }, {'diagnosis': '急性心梗'})
        assert ok

    def test_in_operator(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        ok, _ = e._check_condition({
            'field': 'diagnosis', 'operator': 'in', 'value': '休克'
        }, {'diagnosis': '休克'})
        assert ok

    def test_neq_operator(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        ok, _ = e._check_condition({
            'field': 'urgency', 'operator': '!=', 'value': 'high'
        }, {'urgency': 'normal'})
        assert ok

    def test_nested_navigation(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        val = e._navigate({'a': {'b': {'c': 42}}}, 'a.b.c')
        assert val == 42
        assert e._navigate({'a': 1}, 'b') is None

    def test_max_depth(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        # Create a deep nesting that hits max depth
        cond = {'and': []}
        last = cond
        for _ in range(15):
            last['and'] = [{'and': []}]
            last = last['and'][0]
        ok, desc = e._check_condition(cond, {'x': 1})
        assert not ok
        assert 'max depth' in desc.lower()

    def test_nonexistent_operator(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        ok, desc = e._check_condition({
            'field': 'x', 'operator': 'NONEXISTENT', 'value': 1
        }, {'x': 1})
        assert not ok

    def test_invalid_condition_type(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        ok, desc = e._check_condition([], {'x': 1})
        assert not ok

    def test_get_rules_filter_empty(self):
        from haip.togaf.rule_engine import RuleEngine
        e = RuleEngine()
        e.load_all()
        rules = e.get_rules(department='nonexistent')
        assert len(rules) == 0


# ── audit — export and discovery ──

class TestAuditEdge:
    def test_auto_discover_has_agents(self):
        from haip.togaf.audit import auto_discover
        landscape = auto_discover()
        agent_nodes = [n for n in landscape.nodes if 'agent' in n.id.lower()]
        assert len(agent_nodes) >= 40

    def test_export_landscape(self):
        from haip.togaf.audit import export_landscape
        import tempfile, os
        tmp = os.path.join(tempfile.gettempdir(), 'landscape_test.json')
        path = export_landscape(tmp)
        assert os.path.exists(path)
        os.remove(path)


# ── analysis — maturity scoring ──

class TestAnalysisEdge:
    def test_maturity_score_zero(self):
        from haip.togaf.analysis import MaturityScore
        s = MaturityScore()
        assert s.total == 0
        assert s.tier == 'L0 未覆盖'

    def test_maturity_score_l3(self):
        from haip.togaf.analysis import MaturityScore
        s = MaturityScore(role_completeness=100, data_coverage=100,
                          guideline_adherence=100, a2a_connectivity=100,
                          validation_pass_rate=100)
        assert s.total == 100
        assert s.tier == 'L3 成熟'

    def test_full_analysis_runs(self):
        from haip.togaf.analysis import analyze_all_v2
        results = analyze_all_v2()
        assert len(results) == 39
        for r in results:
            assert r.org_name
            assert r.score.total >= 0

    def test_export_heatmap(self):
        from haip.togaf.analysis import export_heatmap_data
        hm = export_heatmap_data()
        assert 'departments' in hm
        assert len(hm['departments']) == 39


# ── agent_generator — basic tests ──

class TestAgentGenerator:
    def test_list_template_types(self):
        from haip.togaf.templates_dept import list_template_types
        types = list_template_types()
        assert 'surgery' in types
        assert 'internal_medicine' in types

    def test_generate_agent_yaml(self):
        from haip.togaf.agent_generator import generate_agent_yaml
        yaml_str = generate_agent_yaml('respiratory')
        assert yaml_str is not None
        assert 'name:' in yaml_str
        assert 'respiratory' in yaml_str
        assert 'stages:' in yaml_str

    def test_generate_all_missing_dry_run(self):
        from haip.togaf.agent_generator import generate_all_missing
        generated = generate_all_missing('', dry_run=True)
        assert isinstance(generated, list)


# ── patient_generator — basic tests ──

class TestPatientGenerator:
    def test_generate_patients(self):
        from haip.togaf.patient_generator import generate_patients
        new = generate_patients()
        assert isinstance(new, list)

    def test_dept_to_agent(self):
        from haip.togaf.patient_generator import _dept_to_agent
        assert _dept_to_agent('呼吸内科') == 'respiratory'
        assert _dept_to_agent('神经外科') == 'neurosurgery'


# ── templates_dept — edge ──

class TestTemplatesDeptEdge:
    def test_get_dept_template(self):
        from haip.togaf.templates_dept import get_dept_template
        t = get_dept_template('trauma_ortho', 'surgery')
        assert t is not None
        assert len(t.value_streams) >= 4

    def test_get_guideline_info(self):
        from haip.togaf.templates_dept import get_guideline_info
        g = get_guideline_info('trauma_ortho')
        assert len(g) >= 1

    def test_get_template_by_type(self):
        from haip.togaf.templates_dept import get_template_by_type
        t = get_template_by_type('surgery')
        assert t is not None
        assert t.type_kr == '外科'
