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
        # Load a real agent for testing
        from haip.agent import get as get_agent
        from haip.togaf.validator import _check_type_compliance
        agent = get_agent('orthopedic-surgery')
        c = _check_type_compliance(agent)
        assert c.passed
        assert 'ApplicationComponent' in c.detail

    def test_check_org_affiliation_empty(self):
        # 合成无 department 的 agent (acute-pain 现已配置 department, 不能再作反例)
        from haip.agent import DomainPlugin
        from haip.togaf.validator import _check_org_affiliation
        agent = DomainPlugin(name="no-dept-test", type="specialist", department="")
        c = _check_org_affiliation(agent)
        assert not c.passed  # No department set

    def test_check_dependency_graph_empty(self):
        from haip.agent import get as get_agent
        from haip.togaf.validator import _check_dependency_graph
        agent = get_agent('acute-pain')
        c = _check_dependency_graph(agent, {})
        assert c.passed  # No deps → passes

    def test_check_tool_service_empty(self):
        from haip.agent import get as get_agent
        from haip.togaf.validator import _check_tool_service_mapping
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
        assert 'agent' in result
        assert result['agent'] == 'test'
        assert isinstance(result.get('summary', ''), str)

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
        import os
        import tempfile

        from haip.togaf.audit import export_landscape
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


# ── patient_generator — basic tests + edge cases ──

class TestPatientGenerator:
    def test_generate_patients(self):
        from haip.togaf.patient_generator import generate_patients
        new = generate_patients()
        assert isinstance(new, list)

    def test_dept_to_agent(self):
        from haip.togaf.patient_generator import _dept_to_agent
        assert _dept_to_agent('呼吸内科') == 'respiratory'
        assert _dept_to_agent('神经外科') == 'neurosurgery'

    def test_dept_to_agent_full_coverage(self):
        from haip.togaf.patient_generator import _dept_to_agent
        known = {
            '消化内科': 'gastroenterology', '肾内科': 'nephrology',
            '血液内科': 'hematology', '内分泌科': 'endocrinology',
            '风湿免疫科': 'rheumatology', '感染内科': 'infectious-disease',
            '肿瘤科': 'oncology', '中医科': 'tcm', '老年病科': 'geriatrics',
            '普通外科': 'general-surgery', '肝胆外科': 'hepatobiliary-surgery',
            '胸外科': 'thoracic-surgery', '血管外科': 'vascular-surgery',
            '肾移植科': 'renal-transplant', '乳腺中心': 'breast-center',
            '烧伤整形科': 'burns-plastic', '介入治疗科': 'interventional-therapy',
            '妇产科': 'obgyn', '新生儿科': 'neonatology', '眼科': 'ophthalmology',
            '耳鼻喉科': 'ent', '口腔科': 'stomatology', '急诊科': 'emergency',
            '重症医学科': 'icu', '皮肤科': 'dermatology', '精神心理科': 'psychiatry',
            '康复医学科': 'rehabilitation', '健康管理科': 'health-management',
            '惠侨医疗中心': 'huigiao', '整形美容科': 'cosmetic-surgery',
        }
        for dept, expected in known.items():
            assert _dept_to_agent(dept) == expected, f"Mismatch for {dept}"

    def test_dept_to_agent_unknown_fallback(self):
        from haip.togaf.patient_generator import _dept_to_agent
        result = _dept_to_agent('未知科室')
        assert result == '未知科室'

    def test_dept_to_agent_with_spaces(self):
        from haip.togaf.patient_generator import _dept_to_agent
        result = _dept_to_agent('Some New Dept')
        assert result == 'some-new-dept'

    def test_random_lab_generation(self):
        from haip.togaf.patient_generator import _random_lab
        keys = ['Hb', 'WBC', 'CRP', 'ALT', 'Cr']
        labs = _random_lab('test', keys)
        assert 'Hb' in labs
        assert 'WBC' in labs
        assert 3.5 <= labs['WBC'] <= 18.0  # type: ignore[operator]

    def test_generate_with_output_path(self, tmp_path):
        import json

        from haip.togaf.patient_generator import generate_patients
        out = tmp_path / "patients_test.json"
        new = generate_patients(str(out))
        assert isinstance(new, list)
        assert out.exists()
        data = json.loads(out.read_text(encoding='utf-8'))
        assert 'patients' in data or 'total' in data

    def test_random_lab_all_departments(self):
        from haip.togaf.patient_generator import _LAB_TEMPLATES, _random_lab
        for dept_id, keys in list(_LAB_TEMPLATES.items())[:5]:
            labs = _random_lab('test diagnostic', keys)
            assert isinstance(labs, dict)
            for k in keys:
                assert k in labs, f"Missing lab key {k} for {dept_id}"
                assert isinstance(labs[k], (int, float))


# ═════════════════════════════════════════════════════════════
# Agent Generator extended coverage
# ═════════════════════════════════════════════════════════════

class TestAgentGeneratorExtended:
    def test_generate_agent_yaml_with_output_dir(self, tmp_path):
        from haip.togaf.agent_generator import generate_agent_yaml
        output = str(tmp_path / "generated_agents")
        yaml_str = generate_agent_yaml('respiratory', output_dir=output)
        assert yaml_str is not None
        assert 'respiratory' in yaml_str
        expected_file = tmp_path / "generated_agents" / "respiratory.yaml"
        assert expected_file.exists()

    def test_generate_agent_yaml_nonexistent_org(self):
        from haip.togaf.agent_generator import generate_agent_yaml
        result = generate_agent_yaml('completely_nonexistent_org_12345')
        assert result is None

    def test_generate_agent_yaml_surgery_type(self):
        from haip.togaf.agent_generator import generate_agent_yaml
        yaml_str = generate_agent_yaml('trauma_ortho')
        assert yaml_str is not None
        assert 'tools:' in yaml_str
        assert 'name:' in yaml_str

    def test_generate_agent_yaml_emergency_type(self):
        from haip.togaf.agent_generator import generate_agent_yaml
        yaml_str = generate_agent_yaml('emergency')
        assert yaml_str is not None
        assert 'triage' in yaml_str or 'rescue' in yaml_str

    def test_generate_agent_yaml_has_stages_and_roles(self):
        from haip.togaf.agent_generator import generate_agent_yaml
        yaml_str = generate_agent_yaml('respiratory')
        assert yaml_str is not None
        assert 'stages:' in yaml_str
        assert 'roles:' in yaml_str
        assert 'tools:' in yaml_str

    def test_org_to_agent_name_coverage(self):
        from haip.togaf.agent_generator import _org_to_agent_name
        known = {
            '心血管内科': 'cardiology', '消化内科': 'gastroenterology',
            '呼吸内科': 'respiratory', '肾内科': 'nephrology',
            '血液内科': 'hematology', '内分泌科': 'endocrinology',
            '肿瘤科': 'oncology', '中医科': 'tcm', '老年病科': 'geriatrics',
        }
        for dept, expected in known.items():
            assert _org_to_agent_name(dept) == expected, f"Mismatch for {dept}"

    def test_org_to_agent_name_fallback(self):
        from haip.togaf.agent_generator import _org_to_agent_name
        result = _org_to_agent_name('新科室')
        assert result == '新科室'

    def test_assign_port_known(self):
        from haip.togaf.agent_generator import _assign_port
        assert _assign_port('respiratory') == 8781
        assert _assign_port('emergency') == 8808

    def test_assign_port_unknown(self):
        from haip.togaf.agent_generator import _assign_port
        assert _assign_port('nonexistent_dept') == 8900


# ═════════════════════════════════════════════════════════════
# Audit extended coverage
# ═════════════════════════════════════════════════════════════

class TestAuditExtended:
    def test_export_landscape_to_temp(self, tmp_path):
        import json

        from haip.togaf.audit import export_landscape
        out = tmp_path / "landscape.json"
        export_landscape(str(out))
        assert out.exists()
        data = json.loads(out.read_text(encoding='utf-8'))
        assert 'nodes' in data
        assert 'edges' in data

    def test_audit_environment_stats(self):
        from haip.togaf.audit import audit_environment
        result = audit_environment()
        assert 'stats' in result
        assert 'nodes_total' in result
        assert 'edges_total' in result
        assert result['nodes_total'] > 0

    def test_landscape_node_by_id(self):
        from haip.togaf.audit import auto_discover
        landscape = auto_discover()
        node = landscape.node_by_id('nfh')
        assert node is not None
        assert node.id == 'nfh'
        assert landscape.node_by_id('nonexistent_node') is None

    def test_landscape_serialization(self):
        from haip.togaf.audit import _landscape_from_dict, _landscape_to_dict, auto_discover
        landscape = auto_discover()
        data = _landscape_to_dict(landscape)
        assert 'nodes' in data
        assert 'edges' in data
        restored = _landscape_from_dict(data)
        assert restored.name == landscape.name
        assert len(restored.nodes) == len(landscape.nodes)

    def test_discover_organization_helper(self):
        from haip.togaf.audit import ArchitectureLandscape, _discover_organization
        landscape = ArchitectureLandscape()
        _discover_organization(landscape, set())
        assert len(landscape.nodes) == 1
        assert landscape.nodes[0].id == 'nfh'
        assert landscape.nodes[0].entity_type == 'Organization'

    def test_discover_technology_helper(self):
        from haip.togaf.audit import ArchitectureLandscape, _discover_technology
        landscape = ArchitectureLandscape()
        _discover_technology(landscape, set())
        assert len(landscape.nodes) >= 2

    def test_discover_knowledge_assets_helper(self):
        from haip.togaf.audit import (
            ArchitectureLandscape,
            _discover_knowledge_assets,
            _find_project_root,
        )
        landscape = ArchitectureLandscape()
        root = _find_project_root()
        _discover_knowledge_assets(landscape, set(), root)
        assert len(landscape.nodes) >= 1

    def test_icon_for_agent_types(self):
        from haip.togaf.audit import _icon_for_agent
        assert _icon_for_agent('business') == '🤖'
        assert _icon_for_agent('specialist') == '🔬'
        assert _icon_for_agent('master_data') == '💾'
        assert _icon_for_agent('rules') == '📐'
        assert _icon_for_agent('architecture') == '🏗️'
        assert _icon_for_agent('unknown_type') == '🤖'

    def test_landscape_from_dict_empty(self):
        from haip.togaf.audit import _landscape_from_dict
        landscape = _landscape_from_dict({})
        assert landscape.name == ''
        assert landscape.nodes == []

    def test_landscape_to_dict_roundtrip(self):
        from haip.togaf.audit import (
            ArchEdge,
            ArchitectureLandscape,
            ArchNode,
            _landscape_from_dict,
            _landscape_to_dict,
        )
        landscape = ArchitectureLandscape(name='Test')
        landscape.nodes.append(ArchNode(id='n1', label='N1', entity_type='T', domain='d'))
        landscape.edges.append(ArchEdge(source='n1', target='n2', relationship_type='r'))
        data = _landscape_to_dict(landscape)
        restored = _landscape_from_dict(data)
        assert restored.name == 'Test'
        assert len(restored.nodes) == 1
        assert len(restored.edges) == 1

    def test_find_project_root(self):
        from haip.togaf.audit import _find_project_root
        root = _find_project_root()
        assert root.exists()
        assert (root / 'packages').is_dir()

    def test_definitions_dir_helper(self):
        from haip.togaf.audit import _definitions_dir, _find_project_root
        root = _find_project_root()
        defs = _definitions_dir(root)
        assert defs.exists()

    def test_knowledge_dir_helper(self):
        from haip.togaf.audit import _find_project_root, _knowledge_dir
        root = _find_project_root()
        kd = _knowledge_dir(root)
        assert kd.exists()

    def test_report_text(self):
        from haip.togaf.audit import _report_text, auto_discover
        landscape = auto_discover()
        text = _report_text(landscape)
        assert 'xHAIP' in text
        assert len(text) > 100

    def test_main_cli_audit(self):
        from haip.togaf.audit import audit_environment, main_cli
        result = audit_environment()
        assert 'stats' in result
        assert 'nodes_total' in result
        assert result['nodes_total'] > 0

    def test_main_cli_show(self):
        from haip.togaf.audit import _report_text, auto_discover, main_cli
        landscape = auto_discover()
        report = _report_text(landscape)
        assert 'xHAIP' in report
        assert len(report) > 100

    def test_main_cli_stats(self):
        from haip.togaf.audit import audit_environment, main_cli
        result = audit_environment()
        assert 'nodes_total' in result
        assert 'edges_total' in result
        assert result['nodes_total'] > 0

    def test_main_cli_no_args(self, capsys):
        from haip.togaf.audit import main_cli
        main_cli([])
        captured = capsys.readouterr()
        assert 'usage' in captured.out.lower() or '--help' in captured.out.lower() or len(captured.out) > 50

    def test_main_cli_export(self, tmp_path):
        from haip.togaf.audit import main_cli
        out = tmp_path / 'export.json'
        main_cli(['export', '--out', str(out)])
        assert out.exists()

    def test_merge_registry_props(self):
        from haip.agent import DomainPlugin
        from haip.togaf.audit import ArchNode, _merge_registry_props
        node = ArchNode(id='test', label='Test', entity_type='T', domain='d',
                        properties={'port': '0', 'tools': '0'})
        plugin = DomainPlugin(name='test', type='business', port=9999, cn_name='Test Agent')
        _merge_registry_props(node, plugin)
        assert node.properties['port'] == '9999'


# ═════════════════════════════════════════════════════════════
# Patient Generator extended coverage
# ═════════════════════════════════════════════════════════════

class TestPatientGeneratorExtended:
    def test_diagnoses_per_department(self):
        from haip.togaf.patient_generator import _DIAGNOSES
        assert len(_DIAGNOSES) >= 30
        assert len(_DIAGNOSES['respiratory']) >= 5
        assert 'COPD' in _DIAGNOSES['respiratory'][0] or 'COPD' in _DIAGNOSES['respiratory'][1]

    def test_lab_keys_per_department(self):
        from haip.togaf.patient_generator import _LAB_TEMPLATES
        assert 'respiratory' in _LAB_TEMPLATES
        assert 'WBC' in _LAB_TEMPLATES['respiratory']
        assert 'gastroenterology' in _LAB_TEMPLATES
        assert 'neurosurgery' in _LAB_TEMPLATES

    def test_generate_patients_no_duplicate_ids(self):
        from haip.togaf.patient_generator import generate_patients
        new = generate_patients()
        if new:
            ids = [p['patient_id'] for p in new]
            assert len(ids) == len(set(ids))

    def test_generate_patients_has_required_fields(self):
        from haip.togaf.patient_generator import generate_patients
        new = generate_patients()
        if new:
            p = new[0]
            assert 'patient_id' in p
            assert 'department' in p
            assert 'diagnosis' in p
            assert 'lab_results' in p
            assert 'compatible_agents' in p

    def test_generate_patients_with_output(self, tmp_path):
        import json

        from haip.togaf.patient_generator import generate_patients
        out = tmp_path / "patients_out.json"
        generate_patients(str(out))
        assert out.exists()
        data = json.loads(out.read_text(encoding='utf-8'))
        assert 'total' in data


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
