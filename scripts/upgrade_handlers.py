"""Batch-upgrade all handler modules from KnowledgeAgent stubs to RuleEngine-driven."""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MODULES_DIR = ROOT / "packages" / "haip-hospital" / "modules"
# Already upgraded
UPGRADED = {'respiratory', 'cardiology', 'emergency', 'orthopedics', 'cardio_surgery', 
            'pediatrics', 'pharmacy', 'pain_hub', 'togaf', 'medical_record', 'metrics',
            'anesthesia', 'acute_pain', 'cancer_pain', 'chronic_pain', 'interventional_pain', 'pain_rehab'}

upgraded = 0
for name in sorted(os.listdir(MODULES_DIR)):
    if name in UPGRADED:
        continue
    module_dir = os.path.join(MODULES_DIR, name)
    init_file = os.path.join(module_dir, '__init__.py')
    if not os.path.exists(init_file):
        continue

    with open(init_file, encoding='utf-8') as f:
        content = f.read()

    # Skip if already using RuleEngine
    if 'rule_engine' in content and 'run_clinical_pipeline' in content:
        upgraded += 1
        continue

    # Build new content — replace KnowledgeAgent stub pattern
    # Extract dept name and agent name from existing content
    dept_match = re.search(r'department="([^"]+)"', content)
    dept_name = dept_match.group(1) if dept_match else name
    
    agent_match = re.search(r'agent_name="([^"]+)"', content)
    agent_name = agent_match.group(1) if agent_match else name

    new_content = f'''"""{dept_name} — RuleEngine-driven clinical reasoning."""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="{agent_name}", department="{dept_name}")
_agent.rule_engine.load_all()


'''
    # Find all def bp_xxx functions and rewrite them
    func_pattern = r'def (\w+)\(\*\*kwargs\) -> dict:.*?(?=\ndef |\n#|\Z)'
    matches = list(re.finditer(func_pattern, content, re.DOTALL))
    
    if not matches:
        # Try simpler pattern
        funcs = re.finditer(r'def (bp_\w+)\(\*\*kwargs\)', content)
        for m in funcs:
            func_name = m.group(1)
            new_content += f'''def {func_name}(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {{"status": "error", "error": f"Patient {{pid}} not found"}}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

'''
            upgraded += 1
    
    if not matches:
        continue

    for m in matches:
        func_name = m.group(1)
        if func_name.startswith('bp_') or func_name.startswith('def bp_'):
            fname = func_name.replace('def ', '')
            new_content += f'''def {fname}(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {{"status": "error", "error": f"Patient {{pid}} not found"}}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

'''

    with open(init_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    upgraded += 1

print(f'Upgraded {upgraded} handler modules to RuleEngine')
