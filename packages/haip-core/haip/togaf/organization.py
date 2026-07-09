"""Southern Hospital Organization Structure + 184 Role Definitions.

TOGAF 10 Architecture Foundation:
  - Complete hospital org tree (71 departments/offices)
  - 184 RoleDef entries with 9-10 focus areas each
  - Generated from department × role-template matrix

Reference: nfyy.com organization structure (haip-0705-2 organization.py)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OrgNode:
    id: str
    name: str
    type: str  # leadership | admin | clinical | medical_tech | research | education | branch
    parent: str = ""
    description: str = ""
    children: list[OrgNode] = field(default_factory=list)


@dataclass
class RoleDef:
    id: str
    name: str
    org_id: str
    org_name: str
    level: str  # 院领导 | 科主任 | 主治医师 | 住院医师 | 护士长 | 责任护士 | 麻醉医师 | 临床药师 | 医技主任 | 技师 | 科研PI | 研究员 | 教学主任 | 教师
    icon: str
    focus_areas: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class OrgTree:
    roots: list[OrgNode]


# ═══════════════════════════════════════════════════════════
# Role Templates — 14 templates × department type mapping
# ═══════════════════════════════════════════════════════════

# Template: 科主任 (Department Head)
_FOCUS_DEPT_HEAD = [
    "学科建设规划与战略发展方向制定",
    "医疗质量核心指标监控（CMI/RW/低风险死亡率）",
    "重大手术审批与疑难病例 MDT 决策",
    "人才梯队建设（招聘/培养/职称晋升）",
    "科研产出管理（论文/课题/成果转化）",
    "大型设备采购论证与空间规划",
    "科室预算编制与成本核算控制",
    "临床诊疗指南和 SOP 制定与更新",
    "跨科室协作与院内外会诊协调",
    "科室绩效考核与分配方案",
]

# Template: 主治医师 (Attending Physician)
_FOCUS_ATTENDING = [
    "诊断确认与鉴别诊断决策",
    "手术指征评估（绝对/相对/禁忌）",
    "个体化治疗方案制定与调整",
    "围术期并发症风险评估与预防",
    "多学科会诊（MDT）需求判断与发起",
    "临床指南遵循与循证医疗实践",
    "术前讨论主持与手术方案确认",
    "术后管理与康复计划制定",
    "随访计划设计与长期疗效评估",
    "住院医师及实习生带教指导",
]

# Template: 住院医师 (Resident)
_FOCUS_RESIDENT = [
    "病史采集与体格检查标准化操作",
    "医嘱执行与药物剂量核查",
    "病程记录书写（SOAP格式）",
    "检验检查结果追踪与解读",
    "术前准备清单逐项核查",
    "术后患者观察与并发症早期识别",
    "交接班记录完整性与信息传递",
    "患者及家属知情同意沟通",
    "临床技能操作训练（四大穿刺/气管插管等）",
    "参加科室晨会/教学查房/疑难病例讨论",
]

# Template: 护士长 (Head Nurse)
_FOCUS_HEAD_NURSE = [
    "护理质量控制与敏感指标监测",
    "DVT 物理预防方案执行率核查",
    "压疮风险评估（Braden）与预防措施",
    "疼痛评估规范（VAS q4h）与镇痛管理",
    "围术期体位管理（15-30°外展位/轴线翻身）",
    "急救演练组织与护理应急预案制定",
    "院感防控措施执行与手卫生依从性督查",
    "护理耗材申领与成本控制",
    "护理排班与人力调配",
    "出院指导质量评估与家庭护理培训",
]

# Template: 责任护士 (Staff Nurse)
_FOCUS_STAFF_NURSE = [
    "生命体征监测与异常值即时报告",
    "给药执行（三查八对）与药物不良反应观察",
    "各管道护理（胃管/尿管/引流管/深静脉置管）",
    "皮肤护理与压疮预防措施执行",
    "翻身拍背与呼吸功能锻炼指导",
    "健康教育（疾病知识/饮食/运动/用药）",
    "出入量精确记录与液体平衡监测",
    "跌倒风险评估与防护措施落实",
    "心理护理与患者情绪评估",
    "交班报告书写与信息传递准确性",
]

# Template: 麻醉医师 (Anesthesiologist)
_FOCUS_ANESTHESIOLOGIST = [
    "气道评估（Mallampati分级/颈椎活动度/甲颏距离）",
    "ASA分级与围术期风险分层",
    "心血管系统风险评估（RCRI/心脏超声/心肌酶/心电图）",
    "抗凝药物管理与围术期桥接方案",
    "容量状态评估与目标导向液体治疗",
    "凝血功能检测与出血风险评估",
    "药物过敏史核查与麻醉药物选择",
    "术后恶心呕吐（PONV）风险评估与预防",
    "困难气道预案与紧急气道设备准备",
    "术中生命体征监测与麻醉深度调控（BIS）",
]

# Template: 临床药师 (Clinical Pharmacist)
_FOCUS_CLINICAL_PHARMACIST = [
    "营养风险综合评估（NRS2002/MUST/MNA-SF）",
    "处方审核（适应症/用量/配伍/渗透压评分）",
    "药物配伍禁忌检查（钙磷/脂肪乳/阳离子/药物相互作用）",
    "54条风险规则引擎触发与3级判定",
    "TPN处方配比计算（能量/蛋白质/渗透压/阳离子浓度）",
    "治疗药物监测（TDM）与血药浓度解读",
    "药品不良反应（ADR）监测与上报",
    "患者用药教育与依从性评估",
    "临床会诊与药物治疗方案建议",
    "循证药学文献检索与证据评价",
]

# Template: 医技主任 (Medical Tech Director)
_FOCUS_TECH_DIRECTOR = [
    "设备质量控制与性能验证（每日/每周/每月）",
    "检验/检查报告审核与疑难病例复检",
    "新技术新项目引进评估与验证",
    "辐射安全管理与个人剂量监测",
    "试剂耗材管理（效期/冷链/库存）",
    "室间质评参与与结果分析（EQA）",
    "危急值通报流程执行率与时效性监控",
    "标本采集至报告全流程（TAT）优化",
    "医技人员技术培训与能力考核",
    "科研协作与检测方法学研究",
]

# Template: 技师 (Technician)
_FOCUS_TECHNICIAN = [
    "标本接收核对与处理（离心/分装/保存）",
    "仪器设备标准操作规程执行",
    "室内质控执行与失控处理记录",
    "检验/检查结果初步判读与审核",
    "危急值即时通报与记录",
    "仪器日常维护保养与故障报修",
    "试剂耗材领用登记与效期管理",
    "实验室生物安全与消毒隔离",
    "检测原始记录完整性与可追溯性",
    "继续教育学分完成与新技术培训",
]

# Template: 科研PI (Research PI)
_FOCUS_RESEARCH_PI = [
    "科研课题设计与申报（国自然/省自然/横向合作）",
    "科研经费预算编制与合规使用",
    "研究数据质量管控与原始数据保存",
    "伦理委员会审批与知情同意管理",
    "SCI论文撰写/投稿/修改/发表",
    "科研成果转化（专利/软件著作权/临床新技术）",
    "研究团队组建与研究生培养",
    "国内外学术会议参会与交流",
    "知识产权管理与技术秘密保护",
    "实验室安全（生物/化学/辐射）管理",
]

# Template: 研究员 (Researcher)
_FOCUS_RESEARCHER = [
    "实验方案执行与标准操作规程遵循",
    "实验数据采集/记录/初步统计分析",
    "文献检索与综述撰写",
    "实验动物管理（伦理/饲养/麻醉/安乐死）",
    "实验室仪器使用登记与日常维护",
    "生物样本库管理（采集/分装/冻存/信息录入）",
    "论文合作撰写（方法/结果/图表部分）",
    "专利申请技术交底书撰写",
    "实验室试剂耗材采购申请与库存管理",
    "参与课题组学术活动（组会/Journal Club）",
]

# Template: 教学主任 (Education Director)
_FOCUS_EDUCATION_DIRECTOR = [
    "住院医师规范化培训基地建设与管理",
    "医学教育课程体系设计与教学大纲制定",
    "临床技能培训中心规划与设备配置",
    "教学评估（360度评价/Mini-CEX/DOPS）实施",
    "师资队伍建设（教学能力培训/教师资格认定）",
    "实习生与研究生轮转计划安排",
    "教学课题申报与医学教育研究",
    "教学经费预算与教学设备采购",
    "对外教学交流与继续教育项目申报",
    "教学质量监控与持续改进",
]

# Template: 教师 (Teacher)
_FOCUS_TEACHER = [
    "理论授课（大课/小讲课/PBL/CBL）",
    "临床带教（教学查房/病例讨论/床旁教学）",
    "技能操作示范与考核（四大穿刺/缝合/急救）",
    "学生作业/病例报告批改与反馈",
    "实习生病史书写指导与评阅",
    "形成性评价表填写（Mini-CEX/DOPS）",
    "参与教学研究与教学方法创新",
    "继续教育学时完成与教学能力提升",
    "学生思想教育与职业素养引导",
    "教学档案整理（教案/课件/考核记录）",
]


# ═══════════════════════════════════════════════════════════
# Organization Tree — 71 Departments/Offices
# ═══════════════════════════════════════════════════════════

_ORG_TREE_RAW: list[dict] = [
    # ── 院领导 (7) ──
    {"id": "leadership", "name": "院领导班子", "type": "leadership",
     "desc": "医院最高决策层，负责全院发展战略规划与重大事项决策。"},
    {"id": "president", "name": "院长", "type": "leadership", "parent": "leadership",
     "desc": "全面主持医院行政、医疗、教学、科研管理工作。"},
    {"id": "vp-clinic", "name": "医疗副院长", "type": "leadership", "parent": "leadership",
     "desc": "分管医疗业务、医疗质量与安全管理。"},
    {"id": "vp-surgery", "name": "外科副院长", "type": "leadership", "parent": "leadership",
     "desc": "分管外科系统各科室的临床与教学工作。"},
    {"id": "vp-medicine", "name": "内科副院长", "type": "leadership", "parent": "leadership",
     "desc": "分管内科系统、医技科室的临床与科研工作。"},
    {"id": "vp-obgyn-ped", "name": "妇儿副院长", "type": "leadership", "parent": "leadership",
     "desc": "分管妇产科、儿科系统的临床与保健工作。"},
    {"id": "vp-other", "name": "行政副院长", "type": "leadership", "parent": "leadership",
     "desc": "分管特殊科室及跨科室协作业务。"},

    # ── 医院机关 (18) ──
    {"id": "admin", "name": "医院机关", "type": "admin",
     "desc": "行政管理与后勤保障体系。"},
    {"id": "off-general", "name": "医院办公室", "type": "admin", "parent": "admin"},
    {"id": "off-discipline", "name": "纪律检查办公室", "type": "admin", "parent": "admin"},
    {"id": "off-medical", "name": "医务处", "type": "admin", "parent": "admin"},
    {"id": "off-insurance", "name": "医保办公室", "type": "admin", "parent": "admin"},
    {"id": "off-education", "name": "教务处", "type": "admin", "parent": "admin"},
    {"id": "off-student", "name": "学生处", "type": "admin", "parent": "admin"},
    {"id": "off-research", "name": "科研处", "type": "admin", "parent": "admin"},
    {"id": "off-nursing", "name": "护理部", "type": "admin", "parent": "admin"},
    {"id": "off-hr", "name": "人力资源处", "type": "admin", "parent": "admin"},
    {"id": "off-publicity", "name": "宣传处", "type": "admin", "parent": "admin"},
    {"id": "off-security", "name": "保卫处", "type": "admin", "parent": "admin"},
    {"id": "off-audit", "name": "审计处", "type": "admin", "parent": "admin"},
    {"id": "off-finance", "name": "财务处", "type": "admin", "parent": "admin"},
    {"id": "off-logistics", "name": "总务处", "type": "admin", "parent": "admin"},
    {"id": "off-development", "name": "发展处", "type": "admin", "parent": "admin"},
    {"id": "off-union", "name": "工会", "type": "admin", "parent": "admin"},
    {"id": "off-youth", "name": "团委", "type": "admin", "parent": "admin"},

    # ── 职能科室 (9) ──
    {"id": "functional", "name": "职能科室", "type": "admin",
     "desc": "专业职能管理与技术支撑部门。"},
    {"id": "func-health-econ", "name": "卫生经济科", "type": "admin", "parent": "functional"},
    {"id": "func-quality", "name": "质量管理科", "type": "admin", "parent": "functional"},
    {"id": "func-infection", "name": "感染管理科", "type": "admin", "parent": "functional"},
    {"id": "func-prevention", "name": "预防保健科", "type": "admin", "parent": "functional"},
    {"id": "func-it", "name": "信息科", "type": "admin", "parent": "functional"},
    {"id": "func-outpatient", "name": "门诊部", "type": "admin", "parent": "functional"},
    {"id": "func-eng", "name": "医学工程科", "type": "admin", "parent": "functional"},
    {"id": "func-ethics", "name": "伦理委员会", "type": "admin", "parent": "functional"},

    # ── 内科系统 (11) ──
    {"id": "internal_medicine", "name": "内科系统", "type": "clinical",
     "desc": "非手术诊疗的内科临床科室。"},
    {"id": "cardiology", "name": "心血管内科", "type": "clinical", "parent": "internal_medicine"},
    {"id": "gastroenterology", "name": "消化内科", "type": "clinical", "parent": "internal_medicine"},
    {"id": "respiratory", "name": "呼吸内科", "type": "clinical", "parent": "internal_medicine"},
    {"id": "nephrology", "name": "肾内科", "type": "clinical", "parent": "internal_medicine"},
    {"id": "hematology", "name": "血液内科", "type": "clinical", "parent": "internal_medicine"},
    {"id": "endocrinology", "name": "内分泌科", "type": "clinical", "parent": "internal_medicine"},
    {"id": "rheumatology", "name": "风湿免疫科", "type": "clinical", "parent": "internal_medicine"},
    {"id": "infectious_disease", "name": "感染内科", "type": "clinical", "parent": "internal_medicine"},
    {"id": "oncology", "name": "肿瘤科", "type": "clinical", "parent": "internal_medicine"},
    {"id": "tcm", "name": "中医科", "type": "clinical", "parent": "internal_medicine"},
    {"id": "geriatrics", "name": "老年病科", "type": "clinical", "parent": "internal_medicine"},

    # ── 外科系统 (14) ──
    {"id": "surgery", "name": "外科系统", "type": "clinical",
     "desc": "以手术为主要治疗手段的外科临床科室。"},
    {"id": "general_surgery", "name": "普通外科", "type": "clinical", "parent": "surgery"},
    {"id": "hepatobiliary_surgery", "name": "肝胆外科", "type": "clinical", "parent": "surgery"},
    {"id": "trauma_ortho", "name": "创伤骨科", "type": "clinical", "parent": "surgery"},
    {"id": "spine_ortho", "name": "脊柱骨科", "type": "clinical", "parent": "surgery"},
    {"id": "joint_ortho", "name": "关节骨科", "type": "clinical", "parent": "surgery"},
    {"id": "vascular_surgery", "name": "血管外科", "type": "clinical", "parent": "surgery"},
    {"id": "renal_transplant", "name": "肾移植科", "type": "clinical", "parent": "surgery"},
    {"id": "neurosurgery", "name": "神经外科", "type": "clinical", "parent": "surgery"},
    {"id": "thoracic_surgery", "name": "胸外科", "type": "clinical", "parent": "surgery"},
    {"id": "cardio_surgery", "name": "心血管外科", "type": "clinical", "parent": "surgery"},
    {"id": "interventional_therapy", "name": "介入治疗科", "type": "clinical", "parent": "surgery"},
    {"id": "breast_center", "name": "乳腺中心", "type": "clinical", "parent": "surgery"},
    {"id": "burns_plastic", "name": "烧伤整形科", "type": "clinical", "parent": "surgery"},
    {"id": "cosmetic_surgery", "name": "整形美容科", "type": "clinical", "parent": "surgery"},

    # ── 妇产儿科 (3) ──
    {"id": "obgyn_pediatrics", "name": "妇产儿科", "type": "clinical",
     "desc": "妇产科与儿科系统。"},
    {"id": "obgyn", "name": "妇产科", "type": "clinical", "parent": "obgyn_pediatrics"},
    {"id": "pediatrics", "name": "儿科", "type": "clinical", "parent": "obgyn_pediatrics"},
    {"id": "neonatology", "name": "新生儿科", "type": "clinical", "parent": "obgyn_pediatrics"},

    # ── 五官科 (3) ──
    {"id": "ent_oph", "name": "五官科", "type": "clinical",
     "desc": "眼耳鼻喉口腔专科。"},
    {"id": "ophthalmology", "name": "眼科", "type": "clinical", "parent": "ent_oph"},
    {"id": "ent", "name": "耳鼻喉科", "type": "clinical", "parent": "ent_oph"},
    {"id": "stomatology", "name": "口腔科", "type": "clinical", "parent": "ent_oph"},

    # ── 急诊重症 (2) ──
    {"id": "emergency_critical", "name": "急诊重症", "type": "clinical",
     "desc": "急诊与危重症救治体系。"},
    {"id": "emergency", "name": "急诊科", "type": "clinical", "parent": "emergency_critical"},
    {"id": "icu", "name": "重症医学科", "type": "clinical", "parent": "emergency_critical"},

    # ── 其他科室 (6) ──
    {"id": "other_clinical", "name": "其他科室", "type": "clinical",
     "desc": "其他临床与保健康复科室。"},
    {"id": "health_mgmt", "name": "健康管理科", "type": "clinical", "parent": "other_clinical"},
    {"id": "huigiao", "name": "惠侨医疗中心", "type": "clinical", "parent": "other_clinical"},
    {"id": "dermatology", "name": "皮肤科", "type": "clinical", "parent": "other_clinical"},
    {"id": "psychiatry", "name": "精神心理科", "type": "clinical", "parent": "other_clinical"},
    {"id": "rehabilitation", "name": "康复医学科", "type": "clinical", "parent": "other_clinical"},
    {"id": "pain_management", "name": "疼痛科", "type": "clinical", "parent": "other_clinical"},

    # ── 医技科室 (8) ──
    {"id": "medical_technology", "name": "医技科室", "type": "medical_tech",
     "desc": "医学检验、影像、病理等技术支持科室。"},
    {"id": "lab_medicine", "name": "检验科", "type": "medical_tech", "parent": "medical_technology"},
    {"id": "radiology", "name": "影像科", "type": "medical_tech", "parent": "medical_technology"},
    {"id": "pathology", "name": "病理科", "type": "medical_tech", "parent": "medical_technology"},
    {"id": "ultrasound", "name": "超声科", "type": "medical_tech", "parent": "medical_technology"},
    {"id": "nuclear_medicine", "name": "核医学科", "type": "medical_tech", "parent": "medical_technology"},
    {"id": "radiotherapy", "name": "放疗科", "type": "medical_tech", "parent": "medical_technology"},
    {"id": "blood_transfusion", "name": "输血科", "type": "medical_tech", "parent": "medical_technology"},
    {"id": "pharmacy", "name": "药学部", "type": "medical_tech", "parent": "medical_technology"},

    # ── 科研机构 (11) ──
    {"id": "research", "name": "科研机构", "type": "research",
     "desc": "医学研究平台与重点实验室。"},
    {"id": "res-oncology", "name": "肿瘤研究所", "type": "research", "parent": "research"},
    {"id": "res-cardiology", "name": "心血管病研究所", "type": "research", "parent": "research"},
    {"id": "res-neuro", "name": "神经科学研究所", "type": "research", "parent": "research"},
    {"id": "res-digestive", "name": "消化病研究所", "type": "research", "parent": "research"},
    {"id": "res-renal", "name": "肾脏病研究所", "type": "research", "parent": "research"},
    {"id": "res-respiratory", "name": "呼吸病研究所", "type": "research", "parent": "research"},
    {"id": "res-ortho", "name": "骨科研究所", "type": "research", "parent": "research"},
    {"id": "res-infectious", "name": "感染病研究所", "type": "research", "parent": "research"},
    {"id": "res-imaging", "name": "医学影像研究所", "type": "research", "parent": "research"},
    {"id": "res-clinical", "name": "临床研究中心", "type": "research", "parent": "research"},
    {"id": "res-pharmacy", "name": "药物临床试验机构", "type": "research", "parent": "research"},

    # ── 教学机构 (4) ──
    {"id": "education", "name": "教学机构", "type": "education",
     "desc": "医学教育与人才培养体系。"},
    {"id": "edu-internal", "name": "内科教研室", "type": "education", "parent": "education"},
    {"id": "edu-surgery", "name": "外科教研室", "type": "education", "parent": "education"},
    {"id": "edu-nursing", "name": "护理教研室", "type": "education", "parent": "education"},
    {"id": "edu-skills", "name": "临床技能中心", "type": "education", "parent": "education"},

    # ── 分支机构 (4) ──
    {"id": "branches", "name": "分支机构", "type": "branch",
     "desc": "分院及合作共建机构。"},
    {"id": "branch-north", "name": "北院区", "type": "branch", "parent": "branches"},
    {"id": "branch-east", "name": "东院区", "type": "branch", "parent": "branches"},
    {"id": "branch-south", "name": "南院区", "type": "branch", "parent": "branches"},
    {"id": "branch-community", "name": "社区医疗中心", "type": "branch", "parent": "branches"},
]


# ═══════════════════════════════════════════════════════════
# Role Generation — Department × Role Template Matrix
# ═══════════════════════════════════════════════════════════

def _generate_roles() -> dict[str, RoleDef]:
    """Generate 184 role definitions from department × role template matrix."""

    # ── Clinical Departments (34 departments × 3-4 roles = ~126) ──
    _clinical_depts = {
        # 内科
        "cardiology": "心血管内科", "gastroenterology": "消化内科",
        "respiratory": "呼吸内科", "nephrology": "肾内科",
        "hematology": "血液内科", "endocrinology": "内分泌科",
        "rheumatology": "风湿免疫科", "infectious_disease": "感染内科",
        "oncology": "肿瘤科", "tcm": "中医科", "geriatrics": "老年病科",
        # 外科
        "general_surgery": "普通外科", "hepatobiliary_surgery": "肝胆外科",
        "trauma_ortho": "创伤骨科", "spine_ortho": "脊柱骨科",
        "joint_ortho": "关节骨科", "vascular_surgery": "血管外科",
        "renal_transplant": "肾移植科", "neurosurgery": "神经外科",
        "thoracic_surgery": "胸外科", "cardio_surgery": "心血管外科",
        "interventional_therapy": "介入治疗科", "breast_center": "乳腺中心",
        "burns_plastic": "烧伤整形科", "cosmetic_surgery": "整形美容科",
        # 妇产儿科
        "obgyn": "妇产科", "pediatrics": "儿科", "neonatology": "新生儿科",
        # 五官科
        "ophthalmology": "眼科", "ent": "耳鼻喉科", "stomatology": "口腔科",
        # 急诊重症
        "emergency": "急诊科", "icu": "重症医学科",
        # 其他
        "health_mgmt": "健康管理科", "huigiao": "惠侨医疗中心",
        "dermatology": "皮肤科", "psychiatry": "精神心理科",
        "rehabilitation": "康复医学科", "pain_management": "疼痛科",
    }

    _surgery_depts = {
        "trauma_ortho", "spine_ortho", "joint_ortho", "general_surgery",
        "hepatobiliary_surgery", "vascular_surgery", "renal_transplant",
        "neurosurgery", "thoracic_surgery", "cardio_surgery",
        "interventional_therapy", "breast_center", "burns_plastic",
        "cosmetic_surgery", "obgyn",
    }

    role_registry: dict[str, RoleDef] = {}

    # All department name mappings — defined before _add closure
    _dept_names: dict[str, str] = {}

    def _add(role_id: str, name: str, org_id: str, level: str, icon: str,
             focus: list[str], desc: str = ""):
        org_name = _dept_names.get(org_id, org_id)
        role_registry[role_id] = RoleDef(
            id=role_id, name=name, org_id=org_id, org_name=org_name,
            level=level, icon=icon, focus_areas=focus, description=desc,
        )

    # Register clinical department names
    _dept_names.update(_clinical_depts)

    # Clinical departments: 科主任 + 主治 + 住院 + 护士长
    for org_id, org_name in _clinical_depts.items():
        prefix = org_id.replace("_", "")
        _add(f"{prefix}_head", f"{org_name}科主任", org_id, "科主任", "👨‍⚕️",
             [f"{org_name}的" + a for a in _FOCUS_DEPT_HEAD[:8]]
             + ["危急重症救治流程优化与演练",
                "病历质控（甲级病案率≥90%）"])
        _add(f"{prefix}_attending", f"{org_name}主治医师", org_id, "主治医师", "🩺",
             [f"{org_name}领域的" + a for a in _FOCUS_ATTENDING])
        _add(f"{prefix}_resident", f"{org_name}住院医师", org_id, "住院医师", "👨‍🎓",
             _FOCUS_RESIDENT)
        _add(f"{prefix}_head_nurse", f"{org_name}护士长", org_id, "护士长", "👩‍⚕️",
             _FOCUS_HEAD_NURSE)
        # 责任护士 (only for clinical departments)
        _add(f"{prefix}_staff_nurse", f"{org_name}责任护士", org_id, "责任护士", "💉",
             _FOCUS_STAFF_NURSE)
        # 麻醉医师 (only for surgery departments)
        if org_id in _surgery_depts:
            _add(f"{prefix}_anesthesiologist", f"{org_name}麻醉医师", org_id, "麻醉医师", "💉",
                 _FOCUS_ANESTHESIOLOGIST)

    # ── Pharmacy department (special roles) ──
    _add("pharmacy_director", "药学部主任", "pharmacy", "科主任", "💊",
         _FOCUS_DEPT_HEAD + ["药品集中采购与供应链管理", "抗菌药物分级管理"])
    _add("pharmacy_clinical_pharmacist", "临床药师", "pharmacy", "临床药师", "🔬",
         _FOCUS_CLINICAL_PHARMACIST)
    _add("pharmacy_review_pharmacist", "审方药师", "pharmacy", "临床药师", "✅",
         _FOCUS_CLINICAL_PHARMACIST[:5] + [
            "54条规则完整核查与3级判定（提示/警告/禁止）",
            "药品→离子摩尔量换算与阳离子浓度复核",
            "营养液-常用药物相互作用核查",
            "高危药品警示标识与双人核对制度",
            "不合理处方干预与医师沟通反馈",
         ])
    _add("pharmacy_iv_pharmacist", "静脉配置药师", "pharmacy", "临床药师", "🧪",
         _FOCUS_CLINICAL_PHARMACIST[:5] + [
            "渗透压/阳离子浓度/钙磷乘积计算",
            "配液操作流程（8步全合一配制规范）",
            "制剂稳定性评估（避光/破乳/沉淀检查）",
            "PIVAS洁净环境监测（沉降菌/浮游菌/微粒）",
            "配液差错登记与分析改进",
         ])
    _add("pharmacy_head_nurse", "药学部护士长", "pharmacy", "护士长", "👩‍⚕️",
         _FOCUS_HEAD_NURSE[:5] + [
            "PIVAS调配人员手卫生与着装规范督查",
            "药品冷链管理（温度监测/运输验证）",
            "麻醉药品和精神药品安全管理",
            "药品效期管理（预警/下架/报损流程）",
            "药事质控指标（调配差错率/临床药学覆盖率）",
         ])

    # ── Medical Technology Departments (8 × 2 roles = 16) ──
    _tech_depts = {
        "lab_medicine": "检验科", "radiology": "影像科", "pathology": "病理科",
        "ultrasound": "超声科", "nuclear_medicine": "核医学科",
        "radiotherapy": "放疗科", "blood_transfusion": "输血科",
    }
    _dept_names.update(_tech_depts)
    for org_id, org_name in _tech_depts.items():
        prefix = org_id
        _add(f"{prefix}_director", f"{org_name}主任", org_id, "医技主任", "🔬",
             _FOCUS_TECH_DIRECTOR)
        _add(f"{prefix}_technician", f"{org_name}技师", org_id, "技师", "🧫",
             _FOCUS_TECHNICIAN)

    # ── Research Institutions (11 × 2 roles = 22) ──
    _research_depts = {
        "res-oncology": "肿瘤研究所", "res-cardiology": "心血管病研究所",
        "res-neuro": "神经科学研究所", "res-digestive": "消化病研究所",
        "res-renal": "肾脏病研究所", "res-respiratory": "呼吸病研究所",
        "res-ortho": "骨科研究所", "res-infectious": "感染病研究所",
        "res-imaging": "医学影像研究所", "res-clinical": "临床研究中心",
        "res-pharmacy": "药物临床试验机构",
    }
    _dept_names.update(_research_depts)
    for org_id, org_name in _research_depts.items():
        prefix = org_id.replace("-", "")
        _add(f"{prefix}_pi", f"{org_name}PI", org_id, "科研PI", "🔬",
             _FOCUS_RESEARCH_PI)
        _add(f"{prefix}_researcher", f"{org_name}研究员", org_id, "研究员", "🧪",
             _FOCUS_RESEARCHER)

    # ── Education Institutions (4 × 2 roles = 8) ──
    _education_depts = {
        "edu-internal": "内科教研室", "edu-surgery": "外科教研室",
        "edu-nursing": "护理教研室", "edu-skills": "临床技能中心",
    }
    _dept_names.update(_education_depts)
    for org_id, org_name in _education_depts.items():
        prefix = org_id.replace("-", "")
        _add(f"{prefix}_director", f"{org_name}主任", org_id, "教学主任", "📚",
             _FOCUS_EDUCATION_DIRECTOR)
        _add(f"{prefix}_teacher", f"{org_name}教师", org_id, "教师", "📖",
             _FOCUS_TEACHER)

    # ── Admin / Functional departments (not included — admin roles, not clinical) ──

    # ── Leadership (7) ──
    _leadership = {
        "president": ("院长", "院领导", "🏥"),
        "vp-clinic": ("医疗副院长", "院领导", "🏥"),
        "vp-surgery": ("外科副院长", "院领导", "🏥"),
        "vp-medicine": ("内科副院长", "院领导", "🏥"),
        "vp-obgyn-ped": ("妇儿副院长", "院领导", "🏥"),
        "vp-other": ("行政副院长", "院领导", "🏥"),
    }
    _dept_names.update({k: v[0] for k, v in _leadership.items()})
    for org_id, (name, level, icon) in _leadership.items():
        _add(org_id, name, "leadership", level, icon, [
            "全院发展战略规划与重大事项决策",
            "医疗质量与安全管理体系顶层设计",
            "学科布局优化与重点学科建设",
            "年度预算审核与资源配置决策",
            "重大人事任免与人才引进审批",
            "跨部门重大协调事项决策",
            "突发公共卫生事件应急预案决策",
            "对外合作与交流战略规划",
            "医院等级评审与认证工作总负责",
            "信息化建设与数字化转型战略规划",
        ])

    return role_registry


# ═══════════════════════════════════════════════════════════
# Build and Export
# ═══════════════════════════════════════════════════════════

ROLES = _generate_roles()
ROLE_BY_ID: dict[str, RoleDef] = {r.id: r for r in ROLES.values()}
ROLE_BY_ORG: dict[str, list[RoleDef]] = {}
for r in ROLES.values():
    ROLE_BY_ORG.setdefault(r.org_id, []).append(r)


def build_org_tree() -> OrgTree:
    """Build full hospital organization tree from raw definitions."""
    nodes: dict[str, OrgNode] = {}
    for raw in _ORG_TREE_RAW:
        node = OrgNode(
            id=raw["id"],
            name=raw["name"],
            type=raw["type"],
            parent=raw.get("parent", ""),
            description=raw.get("desc", ""),
        )
        nodes[node.id] = node
    # Link children
    for node in nodes.values():
        if node.parent and node.parent in nodes:
            nodes[node.parent].children.append(node)
    roots = [n for n in nodes.values() if not n.parent]
    return OrgTree(roots=roots)


def list_orgs(org_type: str = "") -> list[OrgNode]:
    """List all org nodes, optionally filtered by type."""
    tree = build_org_tree()
    out: list[OrgNode] = []

    def _collect(node: OrgNode):
        if not org_type or node.type == org_type:
            out.append(node)
        for child in node.children:
            _collect(child)

    for root in tree.roots:
        _collect(root)
    return sorted(out, key=lambda n: n.name)


def list_roles(org_id: str = "", level: str = "") -> list[RoleDef]:
    """List all roles, optionally filtered by org_id or level."""
    roles = list(ROLES.values())
    if org_id:
        roles = [r for r in roles if r.org_id == org_id]
    if level:
        roles = [r for r in roles if r.level == level]
    return sorted(roles, key=lambda r: (r.org_name, r.level))


def get_role(role_id: str) -> RoleDef | None:
    return ROLES.get(role_id)


def get_org(org_id: str) -> OrgNode | None:
    nodes = list_orgs()
    for n in nodes:
        if n.id == org_id:
            return n
    return None
