"""Expand patient data with specialty lab fields for RuleEngine matching."""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

random.seed(2026)

# Specialist fields per department type
SPECIALTY_FIELDS = {
    # Surgical
    '神经外科': {'GCS_E': (1,4), 'GCS_V': (1,5), 'GCS_M': (1,6), '瞳孔不等大': (0,0), 'WFNS': (1,5)},
    '胸外科': {'FEV1': (25,95), 'DLCO': (30,95), '结节大小_mm': (3,20)},
    '普通外科': {'ASA': (1,4), 'Blatchford': (0,10), '胆石大小_mm': (3,15)},
    '肝胆外科': {'Child-Pugh': (5,13), 'MELD': (6,30), '肿瘤大小_cm': (2,10), '胆红素': (10,200)},
    '血管外科': {'ABI': (0.2, 1.0), '动脉瘤大小_cm': (3.0, 7.0), 'Rutherford': (0,6), '颈动脉狭窄_pct': (30, 95)},
    '肾移植科': {'交叉配型': (1,1), 'DSA': (100,8000), 'FK506_ng': (2,15)},
    '乳腺中心': {'BI_RADS': (1,5), 'Ki67_pct': (5,80), 'ER_status': (0,1), 'Her2_status': (0,1)},
    '烧伤整形科': {'烧伤面积_pct': (3,40), '深度': (0,1), '吸入性损伤': (0,1)},
    '介入治疗科': {'肿瘤大小_cm': (2,8), '咯血量_ml': (50,500)},
    # Internal medicine
    '消化内科': {'HBsAg': (0,1), 'HBV_DNA': (100,10**6), '便血': (0,1)},
    '肾内科': {'eGFR': (8, 90), '尿蛋白_g': (0.1, 6.0)},
    '血液内科': {'ANC': (100, 5000), '幼稚细胞_pct': (1, 50)},
    '内分泌科': {'TSH': (0.05, 20.0), 'HbA1c': (5.0, 14.0)},
    '风湿免疫科': {'ANA_titer': (1, 1280), 'DAS28': (1.0, 7.0), 'dsDNA': (0,1), 'RF': (10, 300)},
    '感染内科': {'CD4': (50, 800), '乙肝DNA': (10**2, 10**7), '丙肝RNA': (0,1), 'T_SPOT': (0,1)},
    '肿瘤科': {'TNM_stage': (0, 4), 'ECOG': (0, 4), '淋巴结阳性': (0, 1)},
    '老年病科': {'MMSE': (10, 30), '药物种类': (3, 12), '跌倒史': (0, 1)},
    # OBGYN/ENT
    '妇产科': {'宫缩间隔_min': (2, 30), '宫口开大_cm': (1, 10), '蛋白尿': (0, 1)},
    '新生儿科': {'孕周': (28, 41), '黄疸_mg': (5, 20), 'Apgar': (3, 10)},
    '眼科': {'眼压': (12, 35), '视力': (0.02, 1.0), '杯盘比': (0.2, 0.9)},
    '耳鼻喉科': {'听力_dB': (10, 80), '声嘶周数': (1, 12)},
    '口腔科': {'牙周袋_mm': (2, 8), '龋坏深度': (1, 4), '松动度': (0, 3)},
    # Other
    '重症医学科': {'SOFA': (0, 15), '乳酸': (1.0, 8.0), '去甲肾剂量': (0.05, 1.0)},
    '皮肤科': {'皮疹面积_pct': (5, 60), 'ABCDE': (0, 1)},
    '精神心理科': {'PHQ9': (5, 24), 'GAD7': (3, 18), '自杀意念': (0, 1)},
    '康复医学科': {'Barthel': (10, 100), '肌力级': (0, 5), 'Braden': (8, 20)},
    '疼痛科': {'VAS': (0, 10), 'NRS': (0, 10)},
    '健康管理科': {},
    '惠侨医疗中心': {},
    '整形美容科': {'ASA': (1,3), 'BMI': (20, 36)},
}

# Load existing patients
with open(ROOT / "packages" / "haip-hospital" / "data" / "patients.json", encoding='utf-8') as f:
    data = json.load(f)

modified = 0
for p in data['patients']:
    dept = p.get('department', '')
    fields = SPECIALTY_FIELDS.get(dept, {})
    if not fields:
        continue
    
    for field, (lo, hi) in fields.items():
        val = round(random.uniform(lo, hi), 1) if hi - lo > 1 else random.randint(int(lo), int(hi))
        p.setdefault('lab_results', {})[field] = val
    
    # Special handling for pain agents
    if dept == '疼痛科' or 'pain' in str(p.get('compatible_agents', [])):
        p.setdefault('lab_results', {})['VAS'] = random.randint(1, 10)
    
    modified += 1

# Write back
with open(ROOT / "packages" / "haip-hospital" / "data" / "patients.json", 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Expanded {modified} patients with specialty fields')
# Show a sample
for p in data['patients'][:3]:
    extra = {k: v for k, v in p.get('lab_results', {}).items() 
             if k not in ['Hb','WBC','CRP','ALT','Cr','GLU','K+','Troponin','albumin','inr']}
    if extra:
        print(f'  {p["patient_id"]} ({p["department"]}): {list(extra.keys())[:5]}')
