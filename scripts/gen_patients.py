"""Generate 200+ additional digital patients across all departments."""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
random.seed(2026)

# ── Data ──
dept_agents = {
    '呼吸内科': 'respiratory','消化内科': 'gastroenterology','肾内科': 'nephrology',
    '血液内科': 'hematology','内分泌科': 'endocrinology','风湿免疫科': 'rheumatology',
    '感染内科': 'infectious-disease','肿瘤科': 'oncology','中医科': 'tcm',
    '老年病科': 'geriatrics','普通外科': 'general-surgery','肝胆外科': 'hepatobiliary-surgery',
    '神经外科': 'neurosurgery','胸外科': 'thoracic-surgery','血管外科': 'vascular-surgery',
    '肾移植科': 'renal-transplant','乳腺中心': 'breast-center','烧伤整形科': 'burns-plastic',
    '介入治疗科': 'interventional-therapy','妇产科': 'obgyn','新生儿科': 'neonatology',
    '眼科': 'ophthalmology','耳鼻喉科': 'ent','口腔科': 'stomatology',
    '急诊科': 'emergency','重症医学科': 'icu','皮肤科': 'dermatology',
    '精神心理科': 'psychiatry','康复医学科': 'rehabilitation','健康管理科': 'health-management',
    '惠侨医疗中心': 'huigiao','整形美容科': 'cosmetic-surgery',
    '创伤骨科': 'orthopedic-surgery','脊柱骨科': 'orthopedic-surgery','关节骨科': 'orthopedic-surgery',
}

diagnoses = {
    '呼吸内科': ['COPD急性加重','支气管哮喘中度持续','社区获得性肺炎','间质性肺病','肺栓塞','慢性咳嗽','支气管扩张'],
    '消化内科': ['胃食管反流病','慢性胃炎','十二指肠溃疡','肝硬化Child A','急性胰腺炎','结直肠息肉','溃疡性结肠炎'],
    '肾内科': ['慢性肾脏病3期','肾病综合征','IgA肾病','急性肾损伤','糖尿病肾病','高血压肾病'],
    '血液内科': ['缺铁性贫血','骨髓增生异常综合征','急性髓系白血病','多发性骨髓瘤','血小板减少性紫癜'],
    '内分泌科': ['2型糖尿病','甲亢','甲减','骨质疏松症','高脂血症','亚急性甲状腺炎'],
    '风湿免疫科': ['类风湿关节炎','系统性红斑狼疮','强直性脊柱炎','干燥综合征','痛风性关节炎'],
    '感染内科': ['慢性乙型肝炎','丙型肝炎','肺结核','伤寒','艾滋病','感染性心内膜炎'],
    '肿瘤科': ['非小细胞肺癌IIIA','胃癌','肝癌','结直肠癌','乳腺癌','食管鳞癌'],
    '中医科': ['脾胃虚弱','肝肾阴虚','气滞血瘀','风寒感冒','失眠','腰椎间盘突出症'],
    '老年病科': ['老年高血压','老年心衰','老年认知障碍','老年营养不良','老年肌少症'],
    '普通外科': ['急性阑尾炎','胆囊结石','腹股沟疝','肠梗阻','甲状腺结节','胃溃疡穿孔'],
    '肝胆外科': ['肝细胞癌','肝内胆管结石','胆囊癌','胰腺导管癌','肝囊肿'],
    '神经外科': ['脑胶质瘤II','颅脑损伤','高血压脑出血','脑动脉瘤','椎管内肿瘤','垂体腺瘤'],
    '胸外科': ['肺结节','食管中段癌','纵隔肿瘤','胸腺瘤','肺大疱'],
    '血管外科': ['下肢动脉硬化闭塞症','腹主动脉瘤','深静脉血栓','颈动脉狭窄','胸主动脉夹层'],
    '肾移植科': ['终末期肾病','移植肾功能延迟恢复','慢性排斥反应','移植后感染'],
    '乳腺中心': ['乳腺浸润性导管癌','乳腺纤维腺瘤','乳腺导管内癌','乳腺炎'],
    '烧伤整形科': ['面部深度烧伤','手部烧伤','瘢痕挛缩','皮肤软组织缺损'],
    '介入治疗科': ['肝癌介入术后','子宫肌瘤','胆道梗阻','咯血','下肢动脉闭塞'],
    '妇产科': ['异位妊娠','子宫肌瘤','卵巢囊肿','宫颈上皮内瘤变III','盆腔炎','产前检查'],
    '新生儿科': ['新生儿黄疸','早产儿','新生儿窒息','低出生体重','新生儿肺炎'],
    '眼科': ['老年性白内障','开角型青光眼','糖尿病视网膜病变','年龄相关黄斑变性','视网膜脱离'],
    '耳鼻喉科': ['慢性鼻窦炎','过敏性鼻炎','声带息肉','分泌性中耳炎','扁桃体肥大'],
    '口腔科': ['多发性龋齿','慢性牙髓炎','牙周炎','颌面部骨折','口腔白斑'],
    '急诊科': ['急性ST段抬高心梗','急性脑卒中','严重多发伤','过敏性休克','急性中毒','主动脉夹层'],
    '重症医学科': ['脓毒性休克','ARDS重度','急性肾衰竭','严重颅脑损伤','重症急性胰腺炎'],
    '皮肤科': ['寻常型银屑病','特应性皮炎','带状疱疹','慢性荨麻疹','基底细胞癌'],
    '精神心理科': ['重度抑郁发作','广泛性焦虑障碍','双相II型','精神分裂症','强迫症'],
    '康复医学科': ['脑卒中后偏瘫','脊髓损伤截瘫','骨折术后','颈腰椎病','吞咽障碍'],
    '健康管理科': ['年度健康体检','高血压健康管理','糖尿病健康管理','肿瘤筛查'],
    '惠侨医疗中心': ['涉外体检','国际转诊','高端健康管理','慢性病管理'],
    '整形美容科': ['鼻整形','重睑术','吸脂塑形','面部年轻化','乳房整形'],
    '创伤骨科': ['股骨颈骨折','股骨转子间骨折','肱骨近端骨折','桡骨远端骨折','腰椎压缩性骨折','骨盆骨折'],
    '脊柱骨科': ['腰椎间盘突出症','颈椎病','腰椎管狭窄症','脊柱侧弯','胸椎压缩性骨折'],
    '关节骨科': ['膝关节骨关节炎','股骨头坏死','髋关节骨关节炎','肩袖损伤','半月板损伤'],
}

SURNAMES = '李王张刘陈杨赵黄周吴徐孙马胡朱郭何罗林郑梁谢宋唐韩冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段雷钱汤尹黎易常武乔贺赖龚文'

def random_labs(dept, dx):
    labs = {}
    base = {'Hb':(90,165,1),'WBC':(3.5,18,1),'CRP':(1,160,1),'ALT':(12,130,1),'Cr':(45,280,1),'GLU':(3.5,15,1),'K+':(3.3,5.9,1)}
    keys = list(base.keys())[:7]
    for k in keys:
        lo, hi, _ = base[k]
        labs[k] = round(random.uniform(lo, hi), 1)
    if '呼吸' in dept or 'COPD' in dx or '肺' in dx:
        labs.update({'PaO2':round(random.uniform(50,99),1),'FEV1':round(random.uniform(35,95),1)})
    if '心' in dept:
        labs.update({'Troponin':round(random.uniform(0.005,3.5),3),'NT-proBNP':round(random.uniform(50,6000),0)})
    if '肾' in dept:
        labs.update({'BUN':round(random.uniform(5,38),1),'eGFR':round(random.uniform(8,95),0)})
    if '内分泌' in dept or '糖尿' in dx:
        labs.update({'HbA1c':round(random.uniform(5.3,13),1),'TSH':round(random.uniform(0.03,18),2)})
    return labs

# ── Load existing ──
with open(ROOT / "packages" / "haip-hospital" / "data" / "patients.json", encoding='utf-8') as f:
    data = json.load(f)
existing = data.get('patients', [])
next_id = max(int(p['patient_id'][1:]) for p in existing) + 1

# Count existing per dept
dept_counts = {}
for p in existing:
    d = p.get('department', '')
    dept_counts[d] = dept_counts.get(d, 0) + 1

# ── Generate ──
new_patients = []
TARGET = 8

for dept_name, agent_id in dept_agents.items():
    dx_list = diagnoses.get(dept_name, [f'{dept_name}常见病'])
    current = dept_counts.get(dept_name, 0)
    needed = max(0, TARGET - current)
    
    for i in range(needed):
        diagnosis = random.choice(dx_list)
        age = random.randint(22, 84)
        gender = random.choice(['M', 'F'])
        
        compat = [agent_id, 'medical-record']
        if any(k in dept_name for k in ['外科','移植','急诊','重症']):
            compat.extend(['anesthesia-risk'])
        if '外科' in dept_name:
            compat.append('cardio-risk')
        if dept_name == '创伤骨科':
            compat.extend(['cardio-risk','anesthesia-risk','pharmacy'])
        
        patient = {
            'patient_id': f'P{next_id}',
            'name': f'{random.choice(SURNAMES)}*',
            'age': age, 'gender': gender,
            'weight_kg': round(random.uniform(42, 96), 1),
            'height_cm': round(random.uniform(148, 186), 1),
            'department': dept_name,
            'diagnosis': diagnosis,
            'scenario': f'{dept_name}诊疗',
            'lab_results': random_labs(dept_name, diagnosis),
            'compatible_agents': compat,
            'urgency': random.choice(['normal','normal','normal','high']),
        }
        new_patients.append(patient)
        next_id += 1

# ── Specialist cross-references ──
specialists = ['cardio-risk','anesthesia-risk','acute-pain','chronic-pain','cancer-pain','interventional-pain','pain-rehab']
all_patients = existing + new_patients
for sa in specialists:
    samples = random.sample(all_patients, min(60, len(all_patients)))
    count = 0
    for p in samples:
        compat = p.get('compatible_agents', [])
        if sa not in compat:
            p['compatible_agents'] = list(compat) + [sa] if compat else [sa]
            count += 1
        if count >= 8:
            break

# ── Write ──
final = {'total': len(all_patients), 'patients': all_patients}
with open(ROOT / "packages" / "haip-hospital" / "data" / "patients.json", 'w', encoding='utf-8') as f:
    json.dump(final, f, ensure_ascii=False, indent=2)

# ── Report ──
new_counts = {}
for p in all_patients:
    d = p.get('department', '')
    new_counts[d] = new_counts.get(d, 0) + 1

print(f'Added: {len(new_patients)}  Total: {len(all_patients)}')
print(f'Departments: {len(new_counts)}')
for d in sorted(new_counts):
    agt = dept_agents.get(d, '-')
    print(f'  {d:15s} [{agt:25s}] : {new_counts[d]:3d}')
