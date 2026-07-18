"""Final fix: add data_entities and missing guideline to remaining rules."""
import os
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RULES_DIR = ROOT / "packages" / "haip-hospital" / "knowledge" / "rules"

DATA_DE = {
    '急诊科': ('{consumes: [de-lab-cardiac, de-lab-biochemistry, de-lab-hematology, de-lab-infection, de-patient, de-vitals], produces: [de-diagnosis-result, de-risk-assessment]}'),
    '呼吸内科': ('{consumes: [de-lab-pulmonary, de-lab-infection, de-lab-hematology, de-patient], produces: [de-diagnosis-result, de-treatment-plan]}'),
}

MISSING_GUIDES = {
    '呼吸内科': {
        'treatment': 'GOLD 2024 慢性阻塞性肺疾病全球倡议',
        'alert': 'GOLD 2024 慢性阻塞性肺疾病全球倡议',
    },
}

updated = 0
for root, dirs, files in os.walk(RULES_DIR):
    for fname in sorted(files):
        if not fname.endswith('.yaml'):
            continue
        if 'shared' in root or 'clinical_' not in root:
            continue
        fpath = os.path.join(root, fname)
        
        try:
            with open(fpath, encoding='utf-8') as f:
                content = f.read()
            docs = list(yaml.safe_load_all(content))
        except Exception:
            continue
        
        modified = False
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            dept = doc.get('department', '')
            rtype = doc.get('rule_type', '')
            
            if 'data_entities' not in doc and dept in DATA_DE:
                doc['data_entities'] = yaml.safe_load(DATA_DE[dept])
                modified = True
            
            if 'guideline' not in doc:
                g = MISSING_GUIDES.get(dept, {}).get(rtype, '')
                if g:
                    doc['guideline'] = g
                    modified = True
        
        if modified:
            with open(fpath, 'w', encoding='utf-8') as f:
                for i, doc in enumerate(docs):
                    if i > 0:
                        f.write('---\n')
                    yaml.dump(doc, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            updated += 1

# Also fix cardiology rules
cpath = os.path.join(RULES_DIR, 'clinical_cardiology', 'cardiology_rules.yaml')
try:
    with open(cpath, encoding='utf-8') as f:
        docs = list(yaml.safe_load_all(f))
    print(f'Cardiology: {len(docs)} docs loaded successfully')
except Exception as e:
    print(f'Cardiology broken: {e}')

print(f'Updated {updated} files')
