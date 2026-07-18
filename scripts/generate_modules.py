#!/usr/bin/env python3
"""generate_modules.py — Code generator: YAML Agent → Python Module.

Reads agent YAML definitions, clinical guidelines, and rules YAML,
then generates KnowledgeAgent-powered Python modules with real
clinical logic at two quality tiers.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "packages" / "haip-hospital" / "agents" / "definitions"
MODULES_DIR = ROOT / "packages" / "haip-hospital" / "modules"
KNOWLEDGE_DIR = ROOT / "packages" / "haip-hospital" / "knowledge"
GUIDELINES_DIR = KNOWLEDGE_DIR / "guidelines"
RULES_DIR = KNOWLEDGE_DIR / "rules"


# ── Department Clinical Knowledge Base ──────────────────────────────────────

DEPT_KNOWLEDGE: dict[str, dict] = {
    # ═══ Tier B (17 depts) ═══
    "emergency": {
        "cn_name": "急诊科",
        "guideline_files": ["cma-emergency-2023.yaml", "sccm-icu-2021.yaml"],
        "rules_dirs": ["clinical_emergency"],
        "focus": "急危重症快速评估与处理",
        "conditions": ["心脏骤停", "急性脑卒中", "STEMI", "严重多发伤", "急性中毒", "脓毒症"],
        "stage_params": {
            "bp_triage": {"stage": "S1", "desc": "急诊分诊评估", "scoring": "MEWS/NEWS/GCS", "items": ["气道评估", "循环评估", "意识评估", "创伤机制", "中毒筛查"]},
            "bp_rescue": {"stage": "S2", "desc": "紧急救治", "items": ["CPR/ACLS", "除颤", "气道管理", "止血", "解毒剂应用"]},
            "bp_icu": {"stage": "S3", "desc": "重症监护", "scoring": "SOFA/APACHE", "items": ["血流动力学", "呼吸支持", "器官功能", "感染监控"]},
            "bp_transfer": {"stage": "S4", "desc": "转归评估", "items": ["病情稳定判断", "转运风险评估", "接收科室对接"]},
            "bp_followup": {"stage": "S5", "desc": "随访跟踪", "items": ["神经功能恢复", "器官功能随访", "复发风险评估"]},
        },
        "lab_focus": ["Troponin", "D-Dimer", "乳酸", "ABG", "凝血功能"],
        "alerts_checklist": ["意识恶化", "呼吸频率>30或<8", "sBP<90", "SpO2<90%", "尿量<0.5mL/kg/h"],
    },
    "icu": {
        "cn_name": "重症医学科",
        "guideline_files": ["cma-icu-2022.yaml", "sccm-icu-2021.yaml"],
        "rules_dirs": ["clinical_icu"],
        "focus": "多器官功能支持与危重症管理",
        "conditions": ["脓毒症休克", "ARDS", "多器官功能障碍", "术后危重", "严重感染"],
        "stage_params": {
            "bp_triage": {"stage": "S1", "desc": "ICU入科评估", "scoring": "APACHE II/SOFA", "items": ["器官功能基线", "感染指标", "血流动力学", "呼吸状态"]},
            "bp_rescue": {"stage": "S2", "desc": "脏器支持治疗", "items": ["机械通气", "CRRT", "血管活性药物", "ECMO评估"]},
            "bp_icu": {"stage": "S3", "desc": "持续重症监护", "items": ["镇静镇痛管理", "液体管理", "营养支持", "感染监控"]},
            "bp_transfer": {"stage": "S4", "desc": "转出评估", "items": ["脱机评估", "器官功能恢复", "转科风险评估"]},
            "bp_followup": {"stage": "S5", "desc": "ICU后随访", "items": ["PICS评估", "认知功能", "生活质量"]},
        },
        "lab_focus": ["乳酸", "PCT", "ABG", "ScvO2", "Cr", "BUN", "凝血功能"],
        "alerts_checklist": ["SOFA增加≥2", "乳酸>4mmol/L", "血管活性药物递增", "新发器官衰竭", "导管相关感染"],
    },
    "obgyn": {
        "cn_name": "妇产科",
        "guideline_files": ["cma-obgyn-2022.yaml"],
        "rules_dirs": ["clinical_obgyn"],
        "focus": "孕产期管理及妇科疾病诊疗",
        "conditions": ["妊娠期高血压", "妊娠期糖尿病", "产程异常", "妇科肿瘤", "异常子宫出血"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "产科初诊评估", "items": ["孕产次", "孕周", "高危因素", "既往孕产史"]},
            "bp_exam": {"stage": "S2", "desc": "专项检查", "items": ["胎心监护", "B超", "OGTT", "GBS筛查", "宫颈评估"]},
            "bp_diagnosis": {"stage": "S3", "desc": "疾病诊断与分级", "items": ["子痫前期分度", "FGR评估", "胎位判定", "妇科肿瘤分期"]},
            "bp_treatment": {"stage": "S4", "desc": "分娩执行/治疗", "items": ["产程管理", "硫酸镁方案", "终止妊娠时机", "妇科手术方案"]},
            "bp_nursing": {"stage": "S4b", "desc": "产后护理", "items": ["子宫复旧", "恶露观察", "母乳喂养", "新生儿护理"]},
            "bp_followup": {"stage": "S5", "desc": "产后随访", "items": ["42天复查", "盆底康复", "避孕指导", "慢病管理"]},
        },
        "lab_focus": ["Hb", "PLT", "尿蛋白", "OGTT", "TSH", "GBS"],
        "alerts_checklist": ["子痫发作", "胎盘早剥", "产后出血>500mL", "胎儿窘迫", "子宫破裂"],
    },
    "neonatology": {
        "cn_name": "新生儿科",
        "guideline_files": ["cma-neonatology-2022.yaml", "espn-2023.yaml"],
        "rules_dirs": ["clinical_neonatology"],
        "focus": "新生儿疾病筛查与重症救治",
        "conditions": ["新生儿窒息", "早产儿管理", "新生儿黄疸", "新生儿败血症", "NRDS"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "新生儿入院评估", "items": ["Apgar评分", "孕周/出生体重", "分娩方式", "高危因素"]},
            "bp_exam": {"stage": "S2", "desc": "新生儿专项检查", "items": ["血气分析", "血糖监测", "胆红素", "感染指标", "心脏超声"]},
            "bp_diagnosis": {"stage": "S3", "desc": "疾病诊断", "items": ["黄疸分度", "RDS分期", "HIE分级", "感染定位"]},
            "bp_treatment": {"stage": "S4", "desc": "新生儿治疗", "items": ["蓝光治疗", "PS替代", "抗感染", "营养支持", "体温管理"]},
            "bp_followup": {"stage": "S5", "desc": "新生儿随访", "items": ["神经发育", "听力筛查", "ROP筛查", "疫苗接种"]},
        },
        "lab_focus": ["TSB", "CRP", "PCT", "血糖", "ABG", "血培养"],
        "alerts_checklist": ["呼吸暂停", "血氧下降", "喂养不耐受", "体温不稳", "惊厥"],
    },
    "oncology": {
        "cn_name": "肿瘤科",
        "guideline_files": ["csco-oncology-2024.yaml", "nccn-nsclc-2023.yaml", "nccn-breast-2023.yaml"],
        "rules_dirs": ["clinical_oncology"],
        "focus": "肿瘤综合治疗与精准诊疗",
        "conditions": ["肺癌", "乳腺癌", "胃癌", "结直肠癌", "肝癌"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "肿瘤初诊", "items": ["病理类型", "分子分型", "TNM分期", "PS评分"]},
            "bp_exam": {"stage": "S2", "desc": "辅助检查", "items": ["CT/MRI", "PET-CT", "肿瘤标志物", "基因检测", "病理会诊"]},
            "bp_diagnosis": {"stage": "S3", "desc": "确诊分期", "items": ["TNM分期", "分子分型", "预后分层", "MDT讨论"]},
            "bp_plan": {"stage": "S4a", "desc": "治疗计划", "items": ["手术时机", "化疗方案", "靶向药物", "免疫治疗", "放疗计划"]},
            "bp_treatment": {"stage": "S4b", "desc": "治疗执行", "items": ["化疗毒副反应", "靶向药管理", "免疫相关AE", "疗效评估RECIST"]},
            "bp_followup": {"stage": "S5", "desc": "随访管理", "items": ["复发监测", "第二原发癌", "远期毒性", "生存质量"]},
        },
        "lab_focus": ["CEA", "CA19-9", "CA125", "AFP", "NSE", "CYFRA21-1", "基因突变状态"],
        "alerts_checklist": ["肿瘤溶解综合征", "粒缺伴发热", "免疫性肺炎", "VTE", "脊髓压迫"],
    },
    "nephrology": {
        "cn_name": "肾内科",
        "guideline_files": ["kdigo-ckd-2024.yaml"],
        "rules_dirs": ["clinical_nephrology"],
        "focus": "慢性肾脏病管理与替代治疗",
        "conditions": ["慢性肾小球肾炎", "糖尿病肾病", "高血压肾病", "肾病综合征", "AKI"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "肾脏病初诊", "items": ["尿量变化", "水肿", "血压", "既往肾病史"]},
            "bp_exam": {"stage": "S2", "desc": "肾脏专项检查", "items": ["尿常规+沉渣", "24h尿蛋白", "eGFR", "肾脏B超", "自身抗体"]},
            "bp_diagnosis": {"stage": "S3", "desc": "确诊分期", "items": ["CKD分期", "病理类型", "原发病因", "并发症评估"]},
            "bp_plan": {"stage": "S4a", "desc": "治疗方案", "items": ["RAAS阻断", "免疫抑制", "透析时机", "肾移植评估"]},
            "bp_treatment": {"stage": "S4b", "desc": "治疗执行", "items": ["降压达标", "贫血纠正", "钙磷管理", "透析处方"]},
            "bp_followup": {"stage": "S5", "desc": "慢病随访", "items": ["eGFR趋势", "尿蛋白变化", "电解质", "透析充分性"]},
        },
        "lab_focus": ["Cr", "BUN", "eGFR", "尿蛋白", "K+", "Ca", "P", "Hb"],
        "alerts_checklist": ["eGFR下降>25%", "K+>6.0", "严重酸中毒", "尿毒症脑病", "心包炎"],
    },
    "gastroenterology": {
        "cn_name": "消化内科",
        "guideline_files": ["cma-gastritis-2022.yaml"],
        "rules_dirs": ["clinical_gastroenterology"],
        "focus": "消化系统疾病内镜诊疗",
        "conditions": ["消化性溃疡", "IBD", "肝硬化", "胰腺炎", "GERD", "消化道出血"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "消化科初诊", "items": ["腹痛性质", "消化道症状", "大便性状", "黄疸"]},
            "bp_exam": {"stage": "S2", "desc": "消化系统检查", "items": ["胃镜/肠镜", "腹部CT", "肝功能", "HP检测", "肿瘤标志物"]},
            "bp_diagnosis": {"stage": "S3", "desc": "疾病诊断", "items": ["内镜分级", "病理诊断", "肝功能分级", "IBD分型"]},
            "bp_plan": {"stage": "S4a", "desc": "治疗计划", "items": ["PPI方案", "抗HP四联", "IBD生物制剂", "内镜治疗"]},
            "bp_treatment": {"stage": "S4b", "desc": "治疗执行", "items": ["出血止血", "息肉切除", "ERCP", "肝病综合治疗"]},
            "bp_followup": {"stage": "S5", "desc": "随访管理", "items": ["内镜复查", "HP根除确认", "IBD缓解评估", "肝癌筛查"]},
        },
        "lab_focus": ["ALT", "AST", "TBIL", "ALB", "PT", "AMS", "LPS", "HP抗体"],
        "alerts_checklist": ["呕血/黑便", "急性腹痛", "黄疸加重", "腹水增加", "肝性脑病"],
    },
    "neurosurgery": {
        "cn_name": "神经外科",
        "guideline_files": ["cma-neurosurgery-2021.yaml"],
        "rules_dirs": ["clinical_neurosurgery"],
        "focus": "颅脑与脊柱神经外科手术",
        "conditions": ["颅脑损伤", "脑出血", "脑肿瘤", "脊柱退变", "脑血管疾病"],
        "stage_params": {
            "bp_reg": {"stage": "S1", "desc": "患者登记分诊", "items": ["GCS评分", "瞳孔反应", "肢体肌力", "影像初步"]},
            "bp_diag": {"stage": "S2", "desc": "诊断评估", "items": ["CT/MRI", "CTA/DSA", "脑电图", "神经电生理"]},
            "bp_preop": {"stage": "S3", "desc": "术前准备", "items": ["凝血功能", "交叉配血", "麻醉评估", "抗癫痫药物"]},
            "bp_risk": {"stage": "S3b", "desc": "手术风险评估", "items": ["颅内压评估", "脑疝风险", "血管损伤风险", "感染风险"]},
            "bp_mdt": {"stage": "S4a", "desc": "MDT决策", "items": ["术式选择", "手术入路", "术中监测", "备选方案"]},
            "bp_surgery": {"stage": "S4b", "desc": "手术执行", "items": ["开颅/微创", "肿瘤切除", "血肿清除", "动脉瘤夹闭"]},
            "bp_nursing": {"stage": "S4c", "desc": "围术期护理", "items": ["神经功能监测", "颅内压管理", "感染预防", "DVT预防"]},
            "bp_followup": {"stage": "S5", "desc": "术后随访", "items": ["神经功能恢复", "影像复查", "癫痫控制", "康复转介"]},
        },
        "lab_focus": ["凝血功能", "PLT", "电解质", "血糖", "CRP"],
        "alerts_checklist": ["GCS下降≥2", "瞳孔不等大", "新发神经功能缺损", "颅内感染", "癫痫持续状态"],
    },
    "hematology": {
        "cn_name": "血液内科",
        "guideline_files": ["cma-hematology-2022.yaml"],
        "rules_dirs": ["clinical_hematology"],
        "focus": "血液系统疾病诊疗与造血干细胞移植",
        "conditions": ["急性白血病", "淋巴瘤", "多发性骨髓瘤", "MDS", "ITP", "再生障碍性贫血"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "血液科初诊", "items": ["贫血症状", "出血倾向", "发热", "淋巴结肿大"]},
            "bp_exam": {"stage": "S2", "desc": "血液学检查", "items": ["血常规+涂片", "骨髓穿刺", "流式细胞", "细胞遗传学", "分子检测"]},
            "bp_diagnosis": {"stage": "S3", "desc": "确诊分型", "items": ["WHO分型", "危险分层", "基因突变", "预后评分"]},
            "bp_plan": {"stage": "S4a", "desc": "治疗方案", "items": ["化疗方案", "靶向药物", "移植评估", "支持治疗"]},
            "bp_treatment": {"stage": "S4b", "desc": "治疗执行", "items": ["化疗毒副反应", "输血支持", "感染防控", "GVHD管理"]},
            "bp_followup": {"stage": "S5", "desc": "随访管理", "items": ["MRD监测", "复发评估", "远期并发症", "移植后随访"]},
        },
        "lab_focus": ["Hb", "WBC", "PLT", "LDH", "β2-MG", "铁蛋白", "骨髓形态"],
        "alerts_checklist": ["粒缺<0.5", "PLT<20", "DIC", "肿瘤溶解", "严重感染"],
    },
    "rheumatology": {
        "cn_name": "风湿免疫科",
        "guideline_files": ["cma-rheumatology-2022.yaml", "eular-rheumatology-2023.yaml"],
        "rules_dirs": ["clinical_rheumatology"],
        "focus": "自身免疫性疾病诊疗",
        "conditions": ["类风湿关节炎", "SLE", "强直性脊柱炎", "干燥综合征", "痛风", "血管炎"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "风湿科初诊", "items": ["关节肿痛", "皮疹", "雷诺现象", "口干眼干", "发热"]},
            "bp_exam": {"stage": "S2", "desc": "免疫学检查", "items": ["ANA/ENA", "RF/anti-CCP", "HLA-B27", "补体", "炎性指标"]},
            "bp_diagnosis": {"stage": "S3", "desc": "确诊分型", "items": ["ACR/EULAR分类标准", "疾病活动度", "器官受累评估"]},
            "bp_plan": {"stage": "S4a", "desc": "治疗计划", "items": ["DMARDs", "生物制剂", "糖皮质激素", "靶向合成DMARDs"]},
            "bp_treatment": {"stage": "S4b", "desc": "治疗执行", "items": ["免疫抑制监测", "感染筛查", "疫苗接种", "骨质疏松预防"]},
            "bp_followup": {"stage": "S5", "desc": "慢病管理", "items": ["疾病活动度", "药物不良反应", "器官损伤", "生活质量"]},
        },
        "lab_focus": ["ESR", "CRP", "ANA", "抗dsDNA", "RF", "anti-CCP", "C3/C4", "UA"],
        "alerts_checklist": ["狼疮危象", "严重感染", "肾上腺危象", "急性肾损伤", "肺出血"],
    },
    "infectious_disease": {
        "cn_name": "感染内科",
        "guideline_files": ["cma-infectious-2022.yaml"],
        "rules_dirs": ["clinical_infectious_disease"],
        "focus": "感染性疾病诊疗与抗生素管理",
        "conditions": ["肺炎", "泌尿系感染", "腹腔感染", "中枢神经系统感染", "结核病", "HIV/AIDS", "病毒性肝炎"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "感染科初诊", "items": ["发热热型", "感染灶定位", "流行病学史", "免疫状态"]},
            "bp_exam": {"stage": "S2", "desc": "感染相关检查", "items": ["血培养", "PCT/CRP", "病原学检测", "影像学", "药敏试验"]},
            "bp_diagnosis": {"stage": "S3", "desc": "病原诊断", "items": ["病原体鉴定", "感染部位", "严重程度", "耐药评估"]},
            "bp_plan": {"stage": "S4a", "desc": "抗感染方案", "items": ["经验性抗生素", "目标性治疗", "疗程确定", "感染源控制"]},
            "bp_treatment": {"stage": "S4b", "desc": "治疗执行", "items": ["抗菌药物管理", "药物浓度监测", "不良反应", "耐药监测"]},
            "bp_followup": {"stage": "S5", "desc": "随访", "items": ["感染清除确认", "复发监测", "耐药监测", "免疫重建"]},
        },
        "lab_focus": ["WBC", "PCT", "CRP", "血培养", "ESR", "CD4", "病毒载量"],
        "alerts_checklist": ["脓毒症休克", "感染性心内膜炎", "化脓性脑膜炎", "耐药菌感染", "免疫抑制"],
    },
    "geriatrics": {
        "cn_name": "老年病科",
        "guideline_files": ["cma-geriatrics-2023.yaml", "frailty-nursing-consensus.yaml"],
        "rules_dirs": ["clinical_geriatrics"],
        "focus": "老年综合征管理与多病共存",
        "conditions": ["老年衰弱", "认知障碍", "跌倒", "多重用药", "营养不良"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "老年综合评估", "items": ["CGA评估", "ADL/IADL", "跌倒风险", "认知筛查", "营养评估"]},
            "bp_exam": {"stage": "S2", "desc": "老年专项检查", "items": ["认知量表", "步态评估", "骨密度", "听力视力", "多重用药审查"]},
            "bp_diagnosis": {"stage": "S3", "desc": "老年综合征诊断", "items": ["衰弱分级", "认知障碍分期", "肌少症诊断", "营养不良分级"]},
            "bp_plan": {"stage": "S4a", "desc": "综合干预", "items": ["运动处方", "营养支持", "药物精简", "认知训练", "防跌倒"]},
            "bp_treatment": {"stage": "S4b", "desc": "治疗执行", "items": ["慢病管理", "康复训练", "照护计划", "社会支持"]},
            "bp_followup": {"stage": "S5", "desc": "长期随访", "items": ["功能状态变化", "认知轨迹", "再住院", "照护者负担"]},
        },
        "lab_focus": ["Hb", "ALB", "25(OH)D", "Cr", "TSH", "VitB12", "叶酸"],
        "alerts_checklist": ["跌倒", "谵妄", "ADL下降", "体重下降>5%", "多重用药≥5种"],
    },
    "general_surgery": {
        "cn_name": "普通外科",
        "guideline_files": ["cma-general-surgery-2022.yaml"],
        "rules_dirs": ["clinical_general_surgery"],
        "focus": "普外常见疾病手术治疗",
        "conditions": ["阑尾炎", "胆囊结石", "腹股沟疝", "甲状腺结节", "消化道穿孔", "肠梗阻"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "普外初诊", "items": ["腹痛特点", "腹部体征", "既往手术史", "基础疾病"]},
            "bp_exam": {"stage": "S2", "desc": "术前检查", "items": ["腹部CT", "血常规", "凝血功能", "心电图", "感染指标"]},
            "bp_diagnosis": {"stage": "S3", "desc": "手术指征判定", "items": ["急症/择期", "手术方式", "麻醉ASA分级", "风险评估"]},
            "bp_plan": {"stage": "S4a", "desc": "手术计划", "items": ["术前准备", "抗生素预防", "DVT预防", "备血"]},
            "bp_treatment": {"stage": "S4b", "desc": "手术与术后", "items": ["手术记录", "引流管理", "早期下床", "饮食恢复"]},
            "bp_followup": {"stage": "S5", "desc": "术后随访", "items": ["切口愈合", "并发症监测", "病理结果", "功能恢复"]},
        },
        "lab_focus": ["WBC", "CRP", "Hb", "PT", "APTT", "AMS"],
        "alerts_checklist": ["腹膜炎体征", "休克", "肠坏死", "吻合口漏", "腹腔感染"],
    },
    "hepatobiliary_surgery": {
        "cn_name": "肝胆外科",
        "guideline_files": ["cma-hepatobiliary-2022.yaml"],
        "rules_dirs": ["clinical_hepatobiliary"],
        "focus": "肝胆胰脾外科手术",
        "conditions": ["肝癌", "胆道结石", "胰腺肿瘤", "肝硬化门脉高压", "肝血管瘤"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "肝胆科初诊", "items": ["黄疸", "腹痛", "体重下降", "肝炎病史"]},
            "bp_exam": {"stage": "S2", "desc": "肝胆专项检查", "items": ["增强CT/MRI", "MRCP", "肝功能", "肿瘤标志物", "ICG清除"]},
            "bp_diagnosis": {"stage": "S3", "desc": "手术评估", "items": ["肝脏储备", "Child-Pugh分级", "肿瘤可切除性", "门脉高压评估"]},
            "bp_plan": {"stage": "S4a", "desc": "手术计划", "items": ["术式选择", "肝切除范围", "胰十二指肠", "腹腔镜/开腹"]},
            "bp_treatment": {"stage": "S4b", "desc": "手术执行", "items": ["肝门阻断", "胆道重建", "胰肠吻合", "术后肝功能"]},
            "bp_followup": {"stage": "S5", "desc": "术后随访", "items": ["肿瘤复发", "肝功能", "胆道并发症", "营养状态"]},
        },
        "lab_focus": ["ALT", "AST", "TBIL", "ALB", "PT", "AFP", "CA19-9", "ICG-R15"],
        "alerts_checklist": ["肝功能衰竭", "胆漏", "胰漏", "术后出血", "门静脉血栓"],
    },
    "thoracic_surgery": {
        "cn_name": "胸外科",
        "guideline_files": ["cma-thoracic-2022.yaml"],
        "rules_dirs": ["clinical_thoracic_surgery"],
        "focus": "胸部疾病外科治疗",
        "conditions": ["肺癌", "食管癌", "纵隔肿瘤", "气胸", "胸壁畸形", "重症肌无力"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "胸外初诊", "items": ["咳嗽", "胸痛", "气促", "吞咽困难", "吸烟史"]},
            "bp_exam": {"stage": "S2", "desc": "胸部检查", "items": ["胸部CT", "肺功能", "PET-CT", "支气管镜", "食管镜"]},
            "bp_diagnosis": {"stage": "S3", "desc": "手术评估", "items": ["TNM分期", "肺功能储备", "手术耐受性", "MDT讨论"]},
            "bp_plan": {"stage": "S4a", "desc": "手术计划", "items": ["VATS/开胸", "肺叶切除", "食管切除", "淋巴结清扫"]},
            "bp_treatment": {"stage": "S4b", "desc": "手术执行", "items": ["单肺通气", "胸管管理", "疼痛管理", "早期活动"]},
            "bp_followup": {"stage": "S5", "desc": "术后随访", "items": ["肿瘤复发", "肺功能", "生活质量", "辅助治疗"]},
        },
        "lab_focus": ["肺功能FEV1", "DLCO", "ABG", "凝血功能", "肿瘤标志物"],
        "alerts_checklist": ["张力性气胸", "支气管胸膜瘘", "乳糜胸", "肺栓塞", "ARDS"],
    },
    "vascular_surgery": {
        "cn_name": "血管外科",
        "guideline_files": ["cma-vascular-2022.yaml", "esvs-vascular-2022.yaml"],
        "rules_dirs": ["clinical_vascular_surgery"],
        "focus": "血管疾病外科与介入治疗",
        "conditions": ["主动脉瘤", "下肢动脉闭塞", "颈动脉狭窄", "深静脉血栓", "静脉曲张"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "血管外初诊", "items": ["间歇性跛行", "静息痛", "肢体肿胀", "搏动性肿块"]},
            "bp_exam": {"stage": "S2", "desc": "血管专项检查", "items": ["血管超声", "CTA/MRA", "ABI", "DSA", "D-Dimer"]},
            "bp_diagnosis": {"stage": "S3", "desc": "病变评估", "items": ["动脉狭窄分级", "动脉瘤大小", "血栓范围", "手术指征"]},
            "bp_plan": {"stage": "S4a", "desc": "治疗计划", "items": ["开放手术", "腔内介入", "抗凝方案", "溶栓时机"]},
            "bp_treatment": {"stage": "S4b", "desc": "手术执行", "items": ["血管吻合", "支架植入", "取栓", "滤器放置"]},
            "bp_followup": {"stage": "S5", "desc": "远期随访", "items": ["通畅率", "再狭窄", "抗凝管理", "动脉瘤大小"]},
        },
        "lab_focus": ["D-Dimer", "凝血功能", "PLT", "Cr", "血脂"],
        "alerts_checklist": ["动脉瘤破裂", "急性肢体缺血", "肺栓塞", "支架内血栓", "吻合口出血"],
    },
    "interventional_therapy": {
        "cn_name": "介入治疗科",
        "guideline_files": ["cma-interventional-2022.yaml"],
        "rules_dirs": ["clinical_interventional_therapy"],
        "focus": "微创介入诊疗",
        "conditions": ["肝癌TACE", "胆道梗阻PTCD", "消化道出血介入", "肿瘤消融", "血管介入"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "介入科初诊", "items": ["原发病评估", "介入指征", "禁忌症筛查", "影像资料"]},
            "bp_exam": {"stage": "S2", "desc": "介入前检查", "items": ["增强CT/MRI", "血管造影", "肝功能", "凝血功能", "肾功能"]},
            "bp_diagnosis": {"stage": "S3", "desc": "介入评估", "items": ["病变血供", "穿刺路径", "栓塞材料", "风险分层"]},
            "bp_plan": {"stage": "S4a", "desc": "介入方案", "items": ["TACE", "PTCD", "TIPS", "消融", "栓塞"]},
            "bp_treatment": {"stage": "S4b", "desc": "介入操作", "items": ["穿刺安全", "栓塞终点", "造影确认", "并发症处理"]},
            "bp_followup": {"stage": "S5", "desc": "治疗后随访", "items": ["影像评估", "肿瘤反应", "支架通畅", "肝功能"]},
        },
        "lab_focus": ["Cr", "PT", "ALT", "TBIL", "AFP", "WBC"],
        "alerts_checklist": ["穿刺点出血", "异位栓塞", "造影剂肾病", "感染", "肝功能衰竭"],
    },
    "endocrinology": {
        "cn_name": "内分泌科",
        "guideline_files": ["cma-diabetes-2024.yaml", "ada-standards-2025.yaml"],
        "rules_dirs": ["clinical_endocrinology"],
        "focus": "内分泌代谢疾病管理",
        "conditions": ["2型糖尿病", "1型糖尿病", "甲状腺疾病", "骨质疏松", "肥胖症", "肾上腺疾病"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "内分泌初诊", "items": ["血糖水平", "体重变化", "多饮多尿", "甲状腺体征"]},
            "bp_exam": {"stage": "S2", "desc": "内分泌检查", "items": ["血糖/OGTT", "HbA1c", "甲状腺功能", "骨密度", "肾上腺功能"]},
            "bp_diagnosis": {"stage": "S3", "desc": "疾病诊断", "items": ["糖尿病分型", "甲功分类", "代谢综合征", "并发症筛查"]},
            "bp_plan": {"stage": "S4a", "desc": "治疗计划", "items": ["降糖方案", "甲状腺激素", "抗骨质疏松", "生活方式干预"]},
            "bp_treatment": {"stage": "S4b", "desc": "治疗执行", "items": ["血糖监测", "胰岛素调整", "甲功监测", "药物不良反应"]},
            "bp_followup": {"stage": "S5", "desc": "慢病随访", "items": ["HbA1c趋势", "并发症筛查", "生活方式依从", "甲功"]},
        },
        "lab_focus": ["FPG", "HbA1c", "TSH", "FT3", "FT4", "25(OH)D", "ACTH", "皮质醇"],
        "alerts_checklist": ["DKA", "低血糖昏迷", "甲亢危象", "肾上腺危象", "高钙危象"],
    },

    # ═══ Tier C (13 depts) ═══
    "dermatology": {
        "cn_name": "皮肤科",
        "guideline_files": ["cma-dermatology-2022.yaml"],
        "rules_dirs": ["clinical_dermatology"],
        "focus": "常见皮肤病诊疗",
        "conditions": ["湿疹", "银屑病", "荨麻疹", "皮肤感染", "痤疮"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "皮肤科接诊", "items": ["皮疹分布", "瘙痒程度", "病程", "用药史"]},
            "bp_exam": {"stage": "S2", "desc": "皮肤检查", "items": ["皮损形态", "BSA评估", "皮肤镜", "过敏原检测"]},
            "bp_diagnosis": {"stage": "S3", "desc": "疾病诊断", "items": ["皮疹分型", "严重度分级", "鉴别诊断"]},
            "bp_treatment": {"stage": "S4", "desc": "治疗执行", "items": ["外用药", "系统用药", "光疗", "生物制剂"]},
            "bp_followup": {"stage": "S5", "desc": "随访管理", "items": ["疗效评估", "复发监测", "不良反应", "生活指导"]},
        },
        "lab_focus": ["IgE", "过敏原"],
        "alerts_checklist": ["SJS/TEN", "大疱性疾病", "全身性感染"],
    },
    "ent": {
        "cn_name": "耳鼻喉科",
        "guideline_files": ["cma-ent-2022.yaml"],
        "rules_dirs": ["clinical_ent"],
        "focus": "耳鼻喉科常见疾病",
        "conditions": ["慢性鼻窦炎", "中耳炎", "扁桃体炎", "声带息肉", "听力障碍"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "耳鼻喉接诊", "items": ["耳部症状", "鼻部症状", "咽喉症状", "听力"]},
            "bp_exam": {"stage": "S2", "desc": "专科检查", "items": ["鼻内镜", "耳镜", "喉镜", "听力测试", "过敏原"]},
            "bp_diagnosis": {"stage": "S3", "desc": "疾病诊断", "items": ["鼻炎分型", "耳聋分级", "病变定位"]},
            "bp_treatment": {"stage": "S4", "desc": "治疗执行", "items": ["药物治疗", "内镜手术", "听力康复", "语音训练"]},
            "bp_followup": {"stage": "S5", "desc": "随访管理", "items": ["听力变化", "术后恢复", "复发监测"]},
        },
    },
    "stomatology": {
        "cn_name": "口腔科",
        "guideline_files": ["cma-stomatology-2022.yaml"],
        "rules_dirs": ["clinical_stomatology"],
        "focus": "口腔疾病诊疗",
        "conditions": ["龋病", "牙周炎", "口腔溃疡", "颌面外伤", "牙列缺损"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "口腔接诊", "items": ["主诉", "口腔检查", "牙周探诊", "咬合评估"]},
            "bp_exam": {"stage": "S2", "desc": "口腔检查", "items": ["X线片", "CBCT", "牙髓活力", "牙周评估"]},
            "bp_diagnosis": {"stage": "S3", "desc": "疾病诊断", "items": ["龋病分级", "牙周炎分度", "牙髓状态"]},
            "bp_treatment": {"stage": "S4", "desc": "治疗执行", "items": ["补牙/根管", "牙周治疗", "拔牙", "修复"]},
            "bp_followup": {"stage": "S5", "desc": "随访管理", "items": ["口腔卫生", "修复体维护", "牙周维护"]},
        },
    },
    "ophthalmology": {
        "cn_name": "眼科",
        "guideline_files": ["cma-ophthalmology-2022.yaml"],
        "rules_dirs": ["clinical_ophthalmology"],
        "focus": "眼科疾病诊疗",
        "conditions": ["白内障", "青光眼", "糖尿病视网膜病变", "黄斑变性", "屈光不正"],
        "stage_params": {
            "bp_screening": {"stage": "S1", "desc": "眼科筛查", "items": ["视力检查", "眼压", "裂隙灯", "眼底检查"]},
            "bp_exam": {"stage": "S2", "desc": "专科检查", "items": ["OCT", "视野", "眼底照相", "FFA", "生物测量"]},
            "bp_diagnosis": {"stage": "S3", "desc": "疾病诊断", "items": ["白内障分级", "青光眼分期", "DR分级", "AMD分型"]},
            "bp_treatment": {"stage": "S4", "desc": "治疗执行", "items": ["药物", "激光", "手术", "眼内注药"]},
            "bp_followup": {"stage": "S5", "desc": "定期随访", "items": ["视力变化", "眼压控制", "术后恢复", "病变进展"]},
        },
    },
    "rehabilitation": {
        "cn_name": "康复医学科",
        "guideline_files": ["cma-rehabilitation-2022.yaml", "apta-2021.yaml"],
        "rules_dirs": ["clinical_rehabilitation"],
        "focus": "综合康复评估与治疗",
        "conditions": ["脑卒中后", "脊髓损伤", "骨折术后", "关节置换术后", "颈腰椎病"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "康复评估", "items": ["功能评估", "ADL评分", "疼痛评分", "既往康复史"]},
            "bp_exam": {"stage": "S2", "desc": "功能检查", "items": ["肌力测试", "关节活动度", "平衡评估", "步态分析"]},
            "bp_diagnosis": {"stage": "S3", "desc": "功能障碍诊断", "items": ["ICF分类", "康复潜力", "预后评估"]},
            "bp_treatment": {"stage": "S4", "desc": "康复治疗", "items": ["物理治疗", "作业治疗", "言语治疗", "辅助具"]},
            "bp_followup": {"stage": "S5", "desc": "康复随访", "items": ["功能恢复", "社会参与", "生活质量", "重返工作"]},
        },
    },
    "psychiatry": {
        "cn_name": "精神心理科",
        "guideline_files": ["cma-psychiatry-2023.yaml"],
        "rules_dirs": ["clinical_psychiatry"],
        "focus": "精神心理疾病诊疗",
        "conditions": ["抑郁症", "焦虑障碍", "精神分裂症", "双相障碍", "睡眠障碍"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "精神科初诊", "items": ["情绪状态", "精神症状", "自杀风险", "社会功能"]},
            "bp_exam": {"stage": "S2", "desc": "精神检查", "items": ["量表评估", "认知测试", "心理评估", "躯体检查"]},
            "bp_diagnosis": {"stage": "S3", "desc": "诊断分型", "items": ["DSM-5/ICD-11诊断", "严重程度", "共病评估"]},
            "bp_treatment": {"stage": "S4", "desc": "治疗执行", "items": ["药物治疗", "心理治疗", "物理治疗", "社会干预"]},
            "bp_followup": {"stage": "S5", "desc": "随访管理", "items": ["症状变化", "药物依从", "社会功能", "复发预防"]},
        },
    },
    "tcm": {
        "cn_name": "中医科",
        "guideline_files": ["natcm-tcm-2022.yaml"],
        "rules_dirs": ["clinical_tcm"],
        "focus": "中医药辨证论治",
        "conditions": ["脾胃病", "肺系疾病", "心系疾病", "肝肾疾病", "痹症"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "中医初诊", "items": ["望诊", "闻诊", "问诊", "切诊"]},
            "bp_exam": {"stage": "S2", "desc": "辅助检查", "items": ["舌诊", "脉诊", "相关理化检查"]},
            "bp_diagnosis": {"stage": "S3", "desc": "辨证分型", "items": ["八纲辨证", "脏腑辨证", "气血津液辨证"]},
            "bp_treatment": {"stage": "S4", "desc": "治疗执行", "items": ["中药处方", "针灸", "推拿", "中药外治"]},
            "bp_followup": {"stage": "S5", "desc": "随访调理", "items": ["证候变化", "方药调整", "养生指导"]},
        },
    },
    "breast_center": {
        "cn_name": "乳腺中心",
        "guideline_files": ["cma-breast-2022.yaml"],
        "rules_dirs": ["clinical_breast_center"],
        "focus": "乳腺疾病综合诊疗",
        "conditions": ["乳腺癌", "乳腺炎", "乳腺增生", "乳腺纤维瘤"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "乳腺初诊", "items": ["肿块", "溢液", "疼痛", "家族史"]},
            "bp_exam": {"stage": "S2", "desc": "乳腺检查", "items": ["超声", "钼靶", "MRI", "穿刺活检"]},
            "bp_diagnosis": {"stage": "S3", "desc": "疾病诊断", "items": ["BI-RADS", "病理类型", "分子分型"]},
            "bp_treatment": {"stage": "S4", "desc": "综合治疗", "items": ["手术", "化疗", "放疗", "内分泌治疗"]},
            "bp_followup": {"stage": "S5", "desc": "随访管理", "items": ["复发监测", "影像复查", "不良反应", "心理支持"]},
        },
    },
    "burns_plastic": {
        "cn_name": "烧伤整形外科",
        "guideline_files": ["cma-burns-2021.yaml"],
        "rules_dirs": ["clinical_burns_plastic"],
        "focus": "烧伤救治与创面修复",
        "conditions": ["热力烧伤", "化学烧伤", "电烧伤", "瘢痕", "慢性创面"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "烧伤急诊", "items": ["烧伤面积", "深度", "部位", "吸入性损伤"]},
            "bp_exam": {"stage": "S2", "desc": "烧伤评估", "items": ["补液公式", "创面评估", "呼吸道评估", "感染指标"]},
            "bp_diagnosis": {"stage": "S3", "desc": "烧伤诊断", "items": ["烧伤深度", "面积", "严重度分级"]},
            "bp_treatment": {"stage": "S4", "desc": "创面治疗", "items": ["清创", "植皮", "负压治疗", "功能康复"]},
            "bp_followup": {"stage": "S5", "desc": "瘢痕管理", "items": ["瘢痕评估", "压力治疗", "功能训练", "心理康复"]},
        },
    },
    "cosmetic_surgery": {
        "cn_name": "整形美容外科",
        "guideline_files": ["cma-cosmetic-2022.yaml"],
        "rules_dirs": ["clinical_cosmetic_surgery"],
        "focus": "美容整形外科",
        "conditions": ["面部年轻化", "鼻整形", "乳房整形", "脂肪移植", "眼整形"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "美容咨询", "items": ["美学诉求", "期望值", "心理评估", "禁忌症"]},
            "bp_exam": {"stage": "S2", "desc": "术前评估", "items": ["面部/体态评估", "影像学", "化验检查", "凝血功能"]},
            "bp_diagnosis": {"stage": "S3", "desc": "手术方案", "items": ["术式选择", "材料选择", "风险告知"]},
            "bp_treatment": {"stage": "S4", "desc": "手术执行", "items": ["麻醉安全", "手术操作", "术后包扎"]},
            "bp_followup": {"stage": "S5", "desc": "术后管理", "items": ["恢复过程", "并发症", "满意度"]},
        },
    },
    "renal_transplant": {
        "cn_name": "肾移植科",
        "guideline_files": ["cma-transplant-2022.yaml", "kdigo-transplant-2020.yaml"],
        "rules_dirs": ["clinical_renal_transplant"],
        "focus": "肾移植围术期及长期管理",
        "conditions": ["终末期肾病", "肾移植等待", "移植术后管理", "排斥反应"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "移植评估", "items": ["原发肾病", "透析情况", "HLA配型", "供体评估"]},
            "bp_exam": {"stage": "S2", "desc": "移植前检查", "items": ["交叉配型", "感染筛查", "心血管评估", "肿瘤筛查"]},
            "bp_diagnosis": {"stage": "S3", "desc": "移植评估", "items": ["手术风险", "排斥风险评估", "感染风险"]},
            "bp_treatment": {"stage": "S4", "desc": "围术期管理", "items": ["免疫诱导", "免疫维持", "感染预防", "排斥监测"]},
            "bp_followup": {"stage": "S5", "desc": "长期随访", "items": ["肾功能", "药物浓度", "BK病毒", "恶性肿瘤"]},
        },
        "lab_focus": ["Cr", "eGFR", "他克莫司浓度", "BK病毒DNA", "DSA"],
        "alerts_checklist": ["急性排斥", "感染", "药物肾毒性", "原发肾病复发"],
    },
    "health_management": {
        "cn_name": "健康管理/体检中心",
        "guideline_files": ["cma-health-mgmt-2022.yaml", "nhc-2022.yaml"],
        "rules_dirs": ["clinical_health_management"],
        "focus": "健康体检与慢病筛查",
        "conditions": ["健康体检", "慢病筛查", "肿瘤早筛", "心血管风险评估"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "体检登记", "items": ["基本信息", "既往史", "家族史", "生活习惯"]},
            "bp_exam": {"stage": "S2", "desc": "体检检查", "items": ["体格检查", "化验", "影像", "功能检查"]},
            "bp_diagnosis": {"stage": "S3", "desc": "风险评估", "items": ["异常指标", "慢病风险", "肿瘤风险", "心血管风险"]},
            "bp_treatment": {"stage": "S4", "desc": "健康干预", "items": ["生活方式", "营养指导", "运动处方", "疫苗接种"]},
            "bp_followup": {"stage": "S5", "desc": "随访管理", "items": ["定期复查", "风险控制", "健康教育"]},
        },
    },
    "huigiao": {
        "cn_name": "惠侨医疗中心",
        "guideline_files": ["cma-huigiao-2022.yaml"],
        "rules_dirs": ["clinical_huigiao"],
        "focus": "国际医疗与特需服务",
        "conditions": ["国际诊疗", "特需医疗", "医疗转运", "远程会诊"],
        "stage_params": {
            "bp_reception": {"stage": "S1", "desc": "惠侨接诊", "items": ["国际患者", "语言服务", "保险核实", "医疗记录"]},
            "bp_exam": {"stage": "S2", "desc": "检查安排", "items": ["VIP通道", "检查协调", "翻译陪同"]},
            "bp_diagnosis": {"stage": "S3", "desc": "多学科会诊", "items": ["MDT组织", "国际专家", "诊疗方案"]},
            "bp_treatment": {"stage": "S4", "desc": "治疗协调", "items": ["住院安排", "手术绿色通道", "康复计划"]},
            "bp_followup": {"stage": "S5", "desc": "后续管理", "items": ["随访协调", "远程复诊", "国际转运"]},
        },
    },
}


# ── Tier classification ─────────────────────────────────────────────────────

TIER_B = {
    "emergency", "icu", "obgyn", "neonatology", "oncology", "nephrology",
    "gastroenterology", "neurosurgery", "hematology", "rheumatology",
    "infectious_disease", "geriatrics", "general_surgery", "hepatobiliary_surgery",
    "thoracic_surgery", "vascular_surgery", "interventional_therapy", "endocrinology",
}

TIER_C = {
    "dermatology", "ent", "stomatology", "ophthalmology", "rehabilitation",
    "psychiatry", "tcm", "breast_center", "burns_plastic", "cosmetic_surgery",
    "renal_transplant", "health_management", "huigiao",
}


# ── YAML readers ─────────────────────────────────────────────────────────────

def read_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_agent_def(agent_name: str) -> dict | None:
    # Try exact match, then kebab-case conversion
    candidates = [agent_name, agent_name.replace("_", "-")]
    for name in candidates:
        p = AGENTS_DIR / f"{name}.yaml"
        if p.exists():
            return read_yaml(p)
    return None


def load_guideline(filename: str) -> dict | None:
    p = GUIDELINES_DIR / filename
    if p.exists():
        return read_yaml(p)
    return None


def load_rules(rules_dir_name: str) -> list[dict]:
    """Load all rules from a clinical rules directory (multi-doc YAML)."""
    p = RULES_DIR / rules_dir_name
    if not p.exists():
        return []
    results = []
    for yaml_file in sorted(p.glob("*.yaml")):
        try:
            with open(yaml_file, encoding="utf-8") as f:
                docs = list(yaml.safe_load_all(f))
                results.extend([d for d in docs if d is not None])
        except Exception:
            pass
    return results


# ── Code generator core ──────────────────────────────────────────────────────

def _func_body_tier_b(tool_name: str, stage_info: dict, dept: dict) -> str:
    """Generate Tier B function body with real clinical logic."""
    cn = dept["cn_name"]
    stage = stage_info.get("stage", "S1")
    desc = stage_info.get("desc", tool_name)
    items = stage_info.get("items", [])
    scoring = stage_info.get("scoring", "")
    conditions = dept.get("conditions", [])
    alerts = dept.get("alerts_checklist", [])
    lab_focus = dept.get("lab_focus", [])

    # Guideline references
    guide_files = dept.get("guideline_files", [])
    guide_names = []
    for gf in guide_files:
        g = load_guideline(gf)
        if g:
            guide_names.append(g.get("name", gf))
    if not guide_names:
        guide_names = [f"{cn}临床诊疗指南"]
    guide_str = ", ".join(f'"{g}"' for g in guide_names[:3])

    lines = []
    ind = "    "  # 4-space indent

    lines.append(f'{ind}pid = kwargs.get("patient_id", "")')
    lines.append(f"{ind}p = _agent.get_patient(pid)")
    lines.append(f"{ind}if not p:")
    lines.append(f'{ind}{ind}return _clinical_error(f"Patient {{pid}} not found")')
    lines.append(f"{ind}vitals = _agent.assess_vitals(p)")

    # Findings
    finding_items_str = ", ".join(f'"{item}"' for item in items)
    if finding_items_str:
        lines.append(f"{ind}findings = [{finding_items_str}]")
    else:
        lines.append(f'{ind}findings = ["{desc}完成"]')

    if conditions and len(conditions) >= 2:
        c0, c1 = conditions[0], conditions[1]
        lines.append(f'{ind}dx = p.get("diagnosis", "")')
        lines.append(f'{ind}if "{c0[:3]}" in dx or "{c1[:3]}" in dx:')
        lines.append(f'{ind}{ind}findings.insert(0, "{c0}/{c1} 疾病匹配")')

    if alerts:
        alert_vals = ", ".join(f'"{a}"' for a in alerts[:5])
        lines.append(f"{ind}checklist = [{alert_vals}]")
        lines.append(f'{ind}findings.append(f"高危审核: {{len(checklist)}} 项")')

    if lab_focus:
        lab_str = ", ".join(lab_focus[:4])
        lines.append(f"{ind}# 专科检验关注: {lab_str}")
        lines.append(f'{ind}if vitals.get("alerts"):')
        lines.append(f'{ind}{ind}findings.append("检验异常需关注")')

    lines.append(f'{ind}guides = _agent.search_guidelines(p.get("diagnosis", "")) or [{guide_str}]')
    lines.append(f'{ind}rules = _agent.search_rules("{cn}")')

    if scoring:
        lines.append(f"{ind}# Scoring: {scoring}")

    lines.append(f'{ind}return _agent.clinical_result(')
    lines.append(f'{ind}{ind}summary=f"{cn}—{desc}完成 (stage {stage})",')
    lines.append(f"{ind}{ind}patient=p,")
    lines.append(f"{ind}{ind}guidelines=guides,")
    lines.append(f"{ind}{ind}rules=rules,")
    lines.append(f'{ind}{ind}alerts=vitals.get("alerts", []),')
    lines.append(f"{ind})")

    return "\n".join(lines)


def _func_body_tier_c(tool_name: str, stage_info: dict, dept: dict) -> str:
    """Generate Tier C function body (lighter clinical logic)."""
    cn = dept["cn_name"]
    desc = stage_info.get("desc", tool_name)
    items = stage_info.get("items", [])
    stage = stage_info.get("stage", "S1")

    guide_files = dept.get("guideline_files", [])
    guide_names = []
    for gf in guide_files:
        g = load_guideline(gf)
        if g:
            guide_names.append(g.get("name", gf))
    if not guide_names:
        guide_names = [f"{cn}临床诊疗指南"]
    guide_str = ", ".join(f'"{g}"' for g in guide_names[:2])

    lines = []
    ind = "    "
    lines.append(f'{ind}pid = kwargs.get("patient_id", "")')
    lines.append(f"{ind}p = _agent.get_patient(pid)")
    lines.append(f"{ind}if not p:")
    lines.append(f'{ind}{ind}return _clinical_error(f"Patient {{pid}} not found")')
    lines.append(f"{ind}vitals = _agent.assess_vitals(p)")
    lines.append(f'{ind}guides = _agent.search_guidelines(p.get("diagnosis", "")) or [{guide_str}]')

    if items:
        items_str = ", ".join(f'"{item}"' for item in items[:4])
        lines.append(f"{ind}findings = [{items_str}]")
    else:
        lines.append(f'{ind}findings = ["{desc}完成"]')

    lines.append(f"{ind}pipeline = _agent.run_clinical_pipeline(p)")
    lines.append(f"{ind}result = _agent.clinical_result_from_pipeline(p, pipeline)")
    lines.append(f"{ind}result[\"guideline_refs\"] = guides")
    lines.append(f"{ind}result[\"stage\"] = \"{stage}\"")
    lines.append(f'{ind}if vitals.get("alerts"):')
    lines.append(f'{ind}{ind}result["alerts"] = vitals["alerts"]')
    lines.append(f"{ind}return result")
    return "\n".join(lines)



def generate_module(agent_name: str) -> str:
    """Generate a complete module __init__.py for an agent."""
    agent_def = load_agent_def(agent_name)
    if not agent_def:
        return f"# ERROR: No YAML definition found for {agent_name}\n"

    dept = DEPT_KNOWLEDGE.get(agent_name)
    if not dept:
        return f"# WARNING: No knowledge entry for {agent_name}, generating stub\n"

    cn_name = agent_def.get("department", dept["cn_name"])
    tools = agent_def.get("tools", [])
    tier = "B" if agent_name in TIER_B else "C"
    focus = dept.get("focus", "")

    # Guideline names for docstring
    guide_files = dept.get("guideline_files", [])
    guide_names = []
    for gf in guide_files:
        g = load_guideline(gf)
        if g:
            guide_names.append(g.get("name", gf))
    guide_doc = ", ".join(guide_names[:3]) if guide_names else ""

    # Rule engine preload - check if rules dir exists
    rule_dirs = dept.get("rules_dirs", [])
    has_rules = any((RULES_DIR / rd).exists() for rd in rule_dirs)

    lines = []
    lines.append(f'"""{cn_name} — KnowledgeAgent-powered clinical reasoning.')
    lines.append("")
    if focus:
        lines.append(f"Focus: {focus}")
    if guide_doc:
        lines.append(f"GUIDELINES: {guide_doc}")
    if tier == "B":
        conditions = dept.get("conditions", [])
        if conditions:
            lines.append(f"Conditions: {', '.join(conditions[:5])}")
    lines.append('"""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("from haip.togaf.knowledge_agent import KnowledgeAgent")
    lines.append("")
    lines.append(f'_agent = KnowledgeAgent(agent_name="{agent_name}", department="{cn_name}")')

    if guide_names:
        guide_list = ",\n    ".join(f'"{g}"' for g in guide_names[:4])
        lines.append(f"_GUIDELINES = [\n    {guide_list},\n]")
    else:
        lines.append(f'_GUIDELINES = ["{cn_name}临床诊疗指南"]')
    lines.append("")

    if has_rules:
        lines.append("_agent.rule_engine.load_all()")
        lines.append("")

    # Generate functions
    stage_params = dept.get("stage_params", {})
    first = True
    for tool in tools:
        tool_name = tool["name"]
        tool.get("handler", "")
        desc = tool.get("description", f"{tool_name} 业务处理")

        if not first:
            lines.append("")
        first = False

        lines.append("")
        lines.append(f"def {tool_name}(**kwargs) -> dict:")
        lines.append(f'    """{desc}."""')

        stage_info = stage_params.get(tool_name, {"stage": "S1", "desc": desc, "items": []})

        if agent_name in TIER_B:
            body = _func_body_tier_b(tool_name, stage_info, dept)
        else:
            body = _func_body_tier_c(tool_name, stage_info, dept)

        lines.append(body)

    lines.append("")
    return "\n".join(lines)


def inject_error_helper(code: str) -> str:
    """Add clinical_error helper right after KnowledgeAgent imports."""
    # Find the right insertion point: after the _GUIDELINES definition or rule_engine.load_all()
    if "from haip.togaf.knowledge_agent import KnowledgeAgent" in code:
        # We need to add a helper function before the first tool function
        # Find where functions start (def bp_)
        lines = code.split("\n")
        out_lines = []
        inserted = False
        for line in lines:
            out_lines.append(line)
            if not inserted and line.strip().startswith("def bp_"):
                # Insert right before the first function
                # Remove the last line, insert helper, then re-add
                out_lines.pop()
                out_lines.append("")
                out_lines.append("")
                out_lines.append("def _clinical_error(msg: str) -> dict:")
                out_lines.append('    return {"status": "error", "agent": _agent.agent_name, "error": msg}')
                out_lines.append("")
                out_lines.append("")
                out_lines.append(line)
                inserted = True
        code = "\n".join(out_lines)
    
    # Replace _agent.clinical_error( with _clinical_error(
    code = code.replace("_agent.clinical_error(", "_clinical_error(")
    return code


def generate_all(target_agents: list[str] | None = None) -> dict[str, str]:
    """Generate all modules. Returns {agent_name: code}."""
    if target_agents is None:
        target_agents = sorted(TIER_B | TIER_C)

    results = {}
    for name in target_agents:
        code = generate_module(name)
        code = inject_error_helper(code)
        results[name] = code
    return results


def write_modules(results: dict[str, str]) -> list[str]:
    """Write generated modules to disk."""
    written = []
    for name, code in results.items():
        # Handle special module directory names
        module_dir = MODULES_DIR / name
        if not module_dir.exists():
            module_dir.mkdir(parents=True, exist_ok=True)
        init_file = module_dir / "__init__.py"
        with open(init_file, "w", encoding="utf-8") as f:
            f.write(code)
        written.append(name)
    return written


# ── CLI entry ────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate KnowledgeAgent modules from YAML")
    parser.add_argument("--agents", nargs="*", help="Specific agents to generate (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Print instead of writing")
    parser.add_argument("--tier", choices=["B", "C", "all"], default="all", help="Quality tier")
    parser.add_argument("--stats", action="store_true", help="Show module stats only")
    args = parser.parse_args()

    if args.stats:
        total = len(TIER_B) + len(TIER_C)
        print(f"Tier B ({len(TIER_B)}): {', '.join(sorted(TIER_B))}")
        print(f"Tier C ({len(TIER_C)}): {', '.join(sorted(TIER_C))}")
        print(f"Total: {total}")
        return

    if args.tier == "B":
        agents = sorted(TIER_B)
    elif args.tier == "C":
        agents = sorted(TIER_C)
    else:
        agents = sorted(TIER_B | TIER_C)

    if args.agents:
        agents = [a for a in args.agents if a in DEPT_KNOWLEDGE]

    results = generate_all(agents)

    if args.dry_run:
        for name, code in results.items():
            print(f"\n{'='*60}")
            print(f"# Module: {name}")
            print(f"{'='*60}")
            print(code[:500])
            if len(code) > 500:
                print(f"\n... ({len(code)} chars total, {code.count(chr(10))} lines)")
    else:
        written = write_modules(results)
        print(f"Generated {len(written)} modules:")
        for w in sorted(written):
            file_path = MODULES_DIR / w / "__init__.py"
            lines_count = len(results[w].split("\n"))
            tier = "B" if w in TIER_B else "C"
            print(f"  [{tier}] {w:30s} → {file_path} ({lines_count} lines)")
        print(f"\nDone. {len(written)} modules written.")


if __name__ == "__main__":
    main()
