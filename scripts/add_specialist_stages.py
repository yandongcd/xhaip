"""Add stage definitions to specialist agents."""
import yaml, pathlib

d = pathlib.Path(r"D:\dst\projects\xhaip\packages\haip-hospital\agents\definitions")

agents = {
    'acute-pain': [
        {'order':1,'id':'assess','label':'疼痛评估','desc':'NRS/VAS评分、疼痛性质评估、神经病理筛查','role_ids':['attending','nurse']},
        {'order':2,'id':'analgesia','label':'镇痛方案','desc':'WHO阶梯镇痛、PCA参数设定、多模式镇痛','role_ids':['attending']},
        {'order':3,'id':'monitor','label':'效果监测','desc':'疼痛缓解评估、不良反应监测、方案调整','role_ids':['attending','nurse']},
        {'order':4,'id':'followup','label':'随访管理','desc':'慢性疼痛筛查、阿片依赖评估、功能恢复评估','role_ids':['attending']},
    ],
    'anesthesia-risk': [
        {'order':1,'id':'preop','label':'术前评估','desc':'ASA分级、困难气道评估、心血管风险评估','role_ids':['attending','anesthesiologist']},
        {'order':2,'id':'plan','label':'麻醉方案','desc':'麻醉方式选择、用药方案、监测计划','role_ids':['attending','anesthesiologist']},
        {'order':3,'id':'execute','label':'麻醉执行','desc':'诱导与维持、液体管理、体温管理','role_ids':['anesthesiologist','nurse']},
        {'order':4,'id':'postop','label':'术后管理','desc':'PACU监护、疼痛管理、并发症预防','role_ids':['anesthesiologist','nurse']},
    ],
    'cancer-pain': [
        {'order':1,'id':'assess','label':'癌痛评估','desc':'疼痛强度、部位、类型、爆发痛评估','role_ids':['attending']},
        {'order':2,'id':'titration','label':'阿片滴定','desc':'起始剂量、滴定速度、不良反应管理','role_ids':['attending']},
        {'order':3,'id':'maintenance','label':'维持治疗','desc':'长效制剂转换、辅助镇痛药、非药物治疗','role_ids':['attending']},
        {'order':4,'id':'palliative','label':'姑息支持','desc':'终末期疼痛管理、心理支持、家庭照护指导','role_ids':['attending','nurse']},
    ],
    'chronic-pain': [
        {'order':1,'id':'assess','label':'慢痛评估','desc':'疼痛史、功能影响、心理评估、用药史','role_ids':['attending']},
        {'order':2,'id':'multimodal','label':'多模式治疗','desc':'药物+物理治疗+心理干预综合方案','role_ids':['attending','therapist']},
        {'order':3,'id':'review','label':'定期复查','desc':'疗效评估、方案调整、功能恢复评估','role_ids':['attending']},
    ],
    'cardio-risk': [
        {'order':1,'id':'assess','label':'心血管风险评估','desc':'RCRI评分、Goldman指数、运动试验评估','role_ids':['attending']},
        {'order':2,'id':'optimize','label':'术前优化','desc':'血压控制、抗凝管理、心功能优化','role_ids':['attending','cardiologist']},
        {'order':3,'id':'monitor','label':'围术期监测','desc':'ECG监测、心肌标志物、血流动力学','role_ids':['attending','cardiologist']},
    ],
    'interventional-pain': [
        {'order':1,'id':'indication','label':'适应证评估','desc':'介入治疗指征判断、禁忌证筛查','role_ids':['attending']},
        {'order':2,'id':'procedure','label':'介入操作','desc':'神经阻滞/射频/椎体成形术','role_ids':['attending','technician']},
        {'order':3,'id':'followup','label':'术后随访','desc':'疗效评估、并发症监测、重复治疗计划','role_ids':['attending']},
    ],
    'lab-critical-value': [
        {'order':1,'id':'detect','label':'危急值识别','desc':'检验结果筛查、危急值判定、分级预警','role_ids':['technician','attending']},
        {'order':2,'id':'notify','label':'通知处理','desc':'临床科室通知、处理时限跟踪、闭环确认','role_ids':['technician','nurse']},
        {'order':3,'id':'audit','label':'质量审计','desc':'处理合格率统计、延迟分析、改进措施','role_ids':['attending']},
    ],
    'medical-docs': [
        {'order':1,'id':'review','label':'文书审核','desc':'病历完整性审核、诊断编码校验、质控评分','role_ids':['attending','coder']},
        {'order':2,'id':'archive','label':'归档管理','desc':'电子归档、签章确认、借阅管理','role_ids':['coder']},
    ],
    'mdt': [
        {'order':1,'id':'referral','label':'MDT申请','desc':'多学科会诊指征评估、申请提交、资料准备','role_ids':['attending']},
        {'order':2,'id':'consultation','label':'多学科讨论','desc':'各科意见汇总、治疗方案协商、共识达成','role_ids':['attending','surgeon','radiologist','oncologist']},
        {'order':3,'id':'decision','label':'决策执行','desc':'MDT共识落实、方案执行、效果跟踪','role_ids':['attending']},
    ],
    'nurse-general': [
        {'order':1,'id':'admission','label':'入院评估','desc':'护理评估、风险评估、健康教育','role_ids':['nurse']},
        {'order':2,'id':'care-plan','label':'护理计划','desc':'护理诊断、措施制定、评价标准','role_ids':['nurse','head_nurse']},
        {'order':3,'id':'execution','label':'护理执行','desc':'基础护理、专科护理、用药管理','role_ids':['nurse']},
        {'order':4,'id':'discharge','label':'出院指导','desc':'健康宣教、随访计划、社区衔接','role_ids':['nurse']},
    ],
    'pain-management': [
        {'order':1,'id':'assess','label':'疼痛综合评估','desc':'多维度疼痛评估、心理评估、功能评估','role_ids':['attending']},
        {'order':2,'id':'treatment','label':'综合治疗','desc':'药物+介入+康复+心理综合方案','role_ids':['attending','therapist']},
        {'order':3,'id':'followup','label':'随访评估','desc':'疗效评估、方案调整、慢性化预防','role_ids':['attending']},
    ],
    'pain-rehab': [
        {'order':1,'id':'assess','label':'康复评估','desc':'疼痛相关功能障碍评估、康复目标设定','role_ids':['therapist']},
        {'order':2,'id':'rehab','label':'康复治疗','desc':'运动疗法、物理因子、作业治疗','role_ids':['therapist']},
        {'order':3,'id':'evaluate','label':'效果评估','desc':'功能改善评估、重返工作/生活能力评估','role_ids':['therapist','attending']},
    ],
}

for a_name, stages in agents.items():
    yf = d / f"{a_name}.yaml"
    if not yf.exists():
        continue
    with open(yf, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    data["stages"] = stages

    if "ui" not in data:
        data["ui"] = {}
    if "template" not in data["ui"]:
        data["ui"]["template"] = "chat-with-role-switcher"
    if not data["ui"].get("roles"):
        role_ids = set()
        for s in stages:
            role_ids.update(s["role_ids"])
        data["ui"]["roles"] = [{"id": r, "label": r} for r in sorted(role_ids)]

    with open(yf, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=200)
    print(f"  OK: {a_name} ({len(stages)} stages, {len(data['ui']['roles'])} roles)")

print("Done")
