"""TOGAF 科室 4A 分析方法论 v2.0 — Department Type Templates + Guideline Matching.

Layer 2 (规范层): 科室类型模板 + 指南匹配引擎
  从科室类型推导通用价值流和业务流程模板。
  有指南的科室: 指南章节 → 价值流/BP
  无指南的科室: 科室类型模板 → 价值流/BP
"""

from __future__ import annotations

from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════
# 科室类型 × 价值流模板
# ═══════════════════════════════════════════════════════════

@dataclass
class DeptTemplate:
    type_id: str
    name: str
    type_kr: str  # 中文分类名
    value_streams: list[dict]
    business_processes: list[dict]
    common_data_entities: list[str]
    typical_roles: list[str]


# 外科模板 6 阶段
_TEMPLATE_SURGERY = DeptTemplate(
    type_id="surgery",
    name="Surgical Department",
    type_kr="外科",
    value_streams=[
        {"id": "vs-triage", "name": "分诊登记", "stage": 1,
         "trigger": "患者到达", "outcome": "分诊级别"},
        {"id": "vs-assessment", "name": "病情评估", "stage": 2,
         "trigger": "分诊完成", "outcome": "明确诊断"},
        {"id": "vs-decision", "name": "诊疗决策", "stage": 3,
         "trigger": "诊断确认", "outcome": "手术方案 + MDT决策"},
        {"id": "vs-surgery", "name": "手术执行", "stage": 4,
         "trigger": "方案确定", "outcome": "手术完成 + 并发症管理"},
        {"id": "vs-recovery", "name": "术后康复", "stage": 5,
         "trigger": "手术完成", "outcome": "功能恢复 + 随访计划"},
    ],
    business_processes=[
        {"id": "bp-reg", "name": "患者登记分诊", "order": 1, "owner": "主治医师"},
        {"id": "bp-diag", "name": "诊断评估", "order": 2, "owner": "主治医师"},
        {"id": "bp-preop", "name": "术前准备", "order": 3, "owner": "主治医师"},
        {"id": "bp-risk", "name": "风险评估", "order": 4, "owner": "麻醉医师"},
        {"id": "bp-mdt", "name": "MDT决策", "order": 5, "owner": "主治医师"},
        {"id": "bp-surgery", "name": "手术执行", "order": 6, "owner": "主治医师"},
        {"id": "bp-nursing", "name": "围术期护理", "order": 7, "owner": "护士长"},
        {"id": "bp-followup", "name": "术后随访", "order": 8, "owner": "主治医师"},
    ],
    common_data_entities=["患者信息", "检验报告", "影像报告", "手术记录", "随访记录"],
    typical_roles=["主治医师", "住院医师", "护士长", "责任护士", "麻醉医师", "科主任"],
)

# 内科模板 5 阶段
_TEMPLATE_INTERNAL = DeptTemplate(
    type_id="internal_medicine",
    name="Internal Medicine Department",
    type_kr="内科",
    value_streams=[
        {"id": "vs-reception", "name": "接诊登记", "stage": 1,
         "trigger": "患者到达", "outcome": "初步评估"},
        {"id": "vs-assessment", "name": "综合评估", "stage": 2,
         "trigger": "接诊完成", "outcome": "明确诊断 + 分期分级"},
        {"id": "vs-diagnosis", "name": "确诊分型", "stage": 3,
         "trigger": "评估完成", "outcome": "鉴别诊断确认"},
        {"id": "vs-treatment", "name": "治疗执行", "stage": 4,
         "trigger": "诊断确认", "outcome": "治疗方案完成"},
        {"id": "vs-followup", "name": "随访管理", "stage": 5,
         "trigger": "治疗完成", "outcome": "长期管理计划"},
    ],
    business_processes=[
        {"id": "bp-reception", "name": "接诊与初步评估", "order": 1, "owner": "主治医师"},
        {"id": "bp-exam", "name": "辅助检查", "order": 2, "owner": "主治医师"},
        {"id": "bp-diagnosis", "name": "确诊与分型分期", "order": 3, "owner": "主治医师"},
        {"id": "bp-plan", "name": "治疗方案制定", "order": 4, "owner": "主治医师"},
        {"id": "bp-treatment", "name": "治疗执行与监测", "order": 5, "owner": "主治医师"},
        {"id": "bp-followup", "name": "随访与长期管理", "order": 6, "owner": "主治医师"},
    ],
    common_data_entities=["患者信息", "检验报告", "影像报告", "治疗方案", "随访记录"],
    typical_roles=["主治医师", "住院医师", "护士长", "责任护士", "科主任"],
)

# 妇产儿科模板
_TEMPLATE_OBGYN_PED = DeptTemplate(
    type_id="obgyn_pediatrics",
    name="OB/GYN & Pediatrics Department",
    type_kr="妇产儿科",
    value_streams=[
        {"id": "vs-prenatal", "name": "产前/初诊", "stage": 1, "trigger": "就诊", "outcome": "评估分级"},
        {"id": "vs-assessment", "name": "专项评估", "stage": 2, "trigger": "初诊完成", "outcome": "明确诊断"},
        {"id": "vs-delivery", "name": "分娩/治疗", "stage": 3, "trigger": "评估完成", "outcome": "顺利分娩/完成治疗"},
        {"id": "vs-postnatal", "name": "产后/康复", "stage": 4, "trigger": "分娩/治疗完成", "outcome": "母婴/患儿康复"},
        {"id": "vs-followup", "name": "随访保健", "stage": 5, "trigger": "出院", "outcome": "长期健康管理"},
    ],
    business_processes=[
        {"id": "bp-reception", "name": "接诊评估", "order": 1, "owner": "主治医师"},
        {"id": "bp-exam", "name": "专项检查", "order": 2, "owner": "主治医师"},
        {"id": "bp-diagnosis", "name": "诊断分级", "order": 3, "owner": "主治医师"},
        {"id": "bp-treatment", "name": "分娩/治疗执行", "order": 4, "owner": "主治医师"},
        {"id": "bp-nursing", "name": "产后/儿科护理", "order": 5, "owner": "护士长"},
        {"id": "bp-followup", "name": "随访与保健", "order": 6, "owner": "主治医师"},
    ],
    common_data_entities=["患者信息", "检验报告", "超声报告", "分娩/治疗记录", "随访记录"],
    typical_roles=["主治医师", "住院医师", "护士长", "责任护士"],
)

# 五官科模板
_TEMPLATE_ENT = DeptTemplate(
    type_id="ent_oph",
    name="ENT & Ophthalmology Department",
    type_kr="五官科",
    value_streams=[
        {"id": "vs-screening", "name": "筛查初诊", "stage": 1, "trigger": "就诊", "outcome": "初步诊断"},
        {"id": "vs-diagnosis", "name": "确诊评估", "stage": 2, "trigger": "筛查完成", "outcome": "明确诊断"},
        {"id": "vs-treatment", "name": "治疗执行", "stage": 3, "trigger": "诊断确认", "outcome": "治疗完成"},
        {"id": "vs-recovery", "name": "康复恢复", "stage": 4, "trigger": "治疗完成", "outcome": "功能恢复"},
        {"id": "vs-followup", "name": "定期随访", "stage": 5, "trigger": "康复", "outcome": "长期监测"},
    ],
    business_processes=[
        {"id": "bp-screening", "name": "筛查与初诊", "order": 1, "owner": "主治医师"},
        {"id": "bp-exam", "name": "专科检查", "order": 2, "owner": "主治医师"},
        {"id": "bp-diagnosis", "name": "确诊定级", "order": 3, "owner": "主治医师"},
        {"id": "bp-treatment", "name": "治疗操作", "order": 4, "owner": "主治医师"},
        {"id": "bp-followup", "name": "定期复查", "order": 5, "owner": "主治医师"},
    ],
    common_data_entities=["患者信息", "专科检查报告", "影像报告", "治疗记录", "随访记录"],
    typical_roles=["主治医师", "住院医师", "护士长", "责任护士"],
)

# 急诊重症模板
_TEMPLATE_EMERGENCY = DeptTemplate(
    type_id="emergency_critical",
    name="Emergency & ICU Department",
    type_kr="急诊重症",
    value_streams=[
        {"id": "vs-triage", "name": "急诊分诊", "stage": 1, "trigger": "患者到达", "outcome": "分诊级别"},
        {"id": "vs-rescue", "name": "急救处置", "stage": 2, "trigger": "分诊完成", "outcome": "生命体征稳定"},
        {"id": "vs-icu", "name": "重症监护", "stage": 3, "trigger": "急救完成", "outcome": "器官功能支持"},
        {"id": "vs-transfer", "name": "转归处置", "stage": 4, "trigger": "病情稳定", "outcome": "转科/出院"},
        {"id": "vs-followup", "name": "随访跟踪", "stage": 5, "trigger": "出院", "outcome": "康复评估"},
    ],
    business_processes=[
        {"id": "bp-triage", "name": "急诊分诊", "order": 1, "owner": "急诊医师"},
        {"id": "bp-rescue", "name": "紧急救治", "order": 2, "owner": "急诊医师"},
        {"id": "bp-icu", "name": "重症监护", "order": 3, "owner": "ICU医师"},
        {"id": "bp-transfer", "name": "转归评估", "order": 4, "owner": "主治医师"},
        {"id": "bp-followup", "name": "随访跟踪", "order": 5, "owner": "主治医师"},
    ],
    common_data_entities=["患者信息", "生命体征", "检验报告", "影像报告", "转归记录"],
    typical_roles=["主治医师", "住院医师", "护士长", "责任护士"],
)

# 其他科室模板（通用）
_TEMPLATE_OTHER = DeptTemplate(
    type_id="other_clinical",
    name="Other Clinical Department",
    type_kr="其他科室",
    value_streams=[
        {"id": "vs-reception", "name": "接诊评估", "stage": 1, "trigger": "就诊", "outcome": "初步诊断"},
        {"id": "vs-diagnosis", "name": "确诊分型", "stage": 2, "trigger": "评估完成", "outcome": "明确诊断"},
        {"id": "vs-treatment", "name": "治疗执行", "stage": 3, "trigger": "诊断确认", "outcome": "治疗完成"},
        {"id": "vs-recovery", "name": "康复管理", "stage": 4, "trigger": "治疗完成", "outcome": "功能恢复"},
        {"id": "vs-followup", "name": "随访跟踪", "stage": 5, "trigger": "康复", "outcome": "长期管理"},
    ],
    business_processes=[
        {"id": "bp-reception", "name": "接诊评估", "order": 1, "owner": "主治医师"},
        {"id": "bp-exam", "name": "检查检验", "order": 2, "owner": "主治医师"},
        {"id": "bp-diagnosis", "name": "诊断确认", "order": 3, "owner": "主治医师"},
        {"id": "bp-treatment", "name": "治疗执行", "order": 4, "owner": "主治医师"},
        {"id": "bp-followup", "name": "随访管理", "order": 5, "owner": "主治医师"},
    ],
    common_data_entities=["患者信息", "检验报告", "治疗记录", "随访记录"],
    typical_roles=["主治医师", "住院医师", "护士长", "责任护士"],
)

# ═══════════════════════════════════════════════════════════
# Department → Template Mapping
# ═══════════════════════════════════════════════════════════

# Org parent node → template type
_PARENT_TO_TEMPLATE: dict[str, DeptTemplate] = {
    "surgery": _TEMPLATE_SURGERY,
    "internal_medicine": _TEMPLATE_INTERNAL,
    "obgyn_pediatrics": _TEMPLATE_OBGYN_PED,
    "ent_oph": _TEMPLATE_ENT,
    "emergency_critical": _TEMPLATE_EMERGENCY,
    "other_clinical": _TEMPLATE_OTHER,
    "medical_technology": _TEMPLATE_OTHER,
}

# Known guideline mappings: (科室 org_id) → [(指南名, 章节映射)]
_GUIDELINE_REGISTRY: dict[str, list[dict]] = {
    # 外科
    "trauma_ortho": [
        {"name": "国家卫健委2022《老年髋部骨折诊疗与管理指南》", "chapters": 7, "vs": 5, "bp": 10},
        {"name": "NICE NG37 髋部骨折管理 (2023)", "chapters": 6, "vs": 5, "bp": 8},
    ],
    "spine_ortho": [
        {"name": "中华骨科学会 脊柱外科诊疗指南 (2020)", "chapters": 5, "vs": 4, "bp": 6},
    ],
    "joint_ortho": [
        {"name": "AAOS 髋膝关节置换指南 (2022)", "chapters": 6, "vs": 5, "bp": 7},
    ],
    "cardio_surgery": [
        {"name": "AHA/ACC 2020 瓣膜性心脏病管理指南", "chapters": 6, "vs": 5, "bp": 6},
        {"name": "ESC/EACTS 心脏手术围术期指南 (2021)", "chapters": 5, "vs": 4, "bp": 6},
    ],
    "general_surgery": [
        {"name": "中华普外科杂志 普外科诊疗规范 (2022)", "chapters": 5, "vs": 5, "bp": 7},
    ],
    "hepatobiliary_surgery": [
        {"name": "中华肝胆外科杂志 肝切除围术期管理专家共识 (2022)", "chapters": 5, "vs": 5, "bp": 6},
    ],
    "vascular_surgery": [
        {"name": "ESVS 血管外科指南 (2022)", "chapters": 5, "vs": 4, "bp": 6},
    ],
    "neurosurgery": [
        {"name": "中华神经外科杂志 神经外科诊疗规范 (2021)", "chapters": 6, "vs": 5, "bp": 7},
    ],
    "thoracic_surgery": [
        {"name": "NCCN 非小细胞肺癌指南 (2023)", "chapters": 5, "vs": 4, "bp": 6},
    ],
    "renal_transplant": [
        {"name": "KDIGO 肾移植临床实践指南 (2020)", "chapters": 5, "vs": 5, "bp": 6},
    ],
    "breast_center": [
        {"name": "NCCN 乳腺癌指南 (2023)", "chapters": 6, "vs": 5, "bp": 7},
    ],
    "burns_plastic": [
        {"name": "中华烧伤杂志 烧伤诊疗指南 (2021)", "chapters": 5, "vs": 5, "bp": 6},
    ],
    "interventional_therapy": [
        {"name": "中华介入放射学杂志 介入诊疗规范 (2022)", "chapters": 5, "vs": 4, "bp": 5},
    ],
    # 内科
    "cardiology": [
        {"name": "中国心力衰竭诊断和治疗指南 (2024)", "chapters": 6, "vs": 5, "bp": 6},
        {"name": "中国高血压防治指南 (2024)", "chapters": 6, "vs": 5, "bp": 6},
    ],
    "gastroenterology": [
        {"name": "中华消化杂志 消化内镜诊疗指南 (2022)", "chapters": 5, "vs": 5, "bp": 6},
    ],
    "respiratory": [
        {"name": "GOLD 2024 慢性阻塞性肺疾病全球倡议", "chapters": 6, "vs": 5, "bp": 6},
        {"name": "GINA 2024 哮喘管理和预防全球策略", "chapters": 5, "vs": 5, "bp": 5},
    ],
    "nephrology": [
        {"name": "KDIGO 2024 CKD评估与管理指南", "chapters": 5, "vs": 5, "bp": 6},
    ],
    "hematology": [
        {"name": "中华血液学杂志 血液病诊疗指南 (2022)", "chapters": 5, "vs": 5, "bp": 6},
    ],
    "endocrinology": [
        {"name": "中国2型糖尿病防治指南 (2024)", "chapters": 6, "vs": 5, "bp": 6},
        {"name": "中国甲状腺疾病诊治指南 (2023)", "chapters": 5, "vs": 5, "bp": 5},
    ],
    "rheumatology": [
        {"name": "EULAR 2023 类风湿关节炎管理指南", "chapters": 5, "vs": 5, "bp": 6},
    ],
    "infectious_disease": [
        {"name": "中华感染杂志 感染性疾病诊疗规范 (2022)", "chapters": 5, "vs": 5, "bp": 6},
    ],
    "oncology": [
        {"name": "中国临床肿瘤学会 CSCO 指南 (2024)", "chapters": 6, "vs": 5, "bp": 7},
    ],
    "tcm": [
        {"name": "国家中医药管理局 中医诊疗方案 (2022)", "chapters": 5, "vs": 5, "bp": 6},
    ],
    "geriatrics": [
        {"name": "中国老年医学学会 老年综合评估指南 (2023)", "chapters": 5, "vs": 5, "bp": 6},
    ],
    # 妇产儿科
    "obgyn": [
        {"name": "中华妇产科杂志 产前检查与诊疗指南 (2022)", "chapters": 6, "vs": 5, "bp": 6},
    ],
    "neonatology": [
        {"name": "中华儿科杂志 新生儿诊疗规范 (2022)", "chapters": 5, "vs": 5, "bp": 6},
    ],
    # 五官科
    "ophthalmology": [
        {"name": "中华眼科杂志 眼科诊疗指南 (2022)", "chapters": 5, "vs": 4, "bp": 5},
    ],
    "ent": [
        {"name": "中华耳鼻咽喉头颈外科杂志 诊疗指南 (2022)", "chapters": 5, "vs": 4, "bp": 5},
    ],
    "stomatology": [
        {"name": "中华口腔医学杂志 口腔诊疗规范 (2022)", "chapters": 5, "vs": 4, "bp": 5},
    ],
    # 急诊重症
    "emergency": [
        {"name": "中国急诊医学杂志 急诊诊疗指南 (2023)", "chapters": 6, "vs": 5, "bp": 6},
    ],
    "icu": [
        {"name": "SCCM 2021 重症监护管理指南", "chapters": 6, "vs": 5, "bp": 6},
    ],
    # 其他
    "dermatology": [
        {"name": "中华皮肤科杂志 皮肤病诊疗指南 (2022)", "chapters": 5, "vs": 4, "bp": 5},
    ],
    "psychiatry": [
        {"name": "中国精神障碍防治指南 (2023)", "chapters": 6, "vs": 5, "bp": 6},
    ],
    "rehabilitation": [
        {"name": "中华康复医学杂志 康复诊疗指南 (2022)", "chapters": 5, "vs": 5, "bp": 5},
    ],
    "pain_management": [
        {"name": "中国疼痛医学杂志 疼痛诊疗规范 (2022)", "chapters": 5, "vs": 5, "bp": 6},
    ],
    "health_mgmt": [
        {"name": "中华健康管理学杂志 健康体检指南 (2022)", "chapters": 5, "vs": 4, "bp": 5},
    ],
}

_TEMPLATE_REGISTRY: dict[str, DeptTemplate] = {
    "surgery": _TEMPLATE_SURGERY,
    "internal_medicine": _TEMPLATE_INTERNAL,
    "obgyn_pediatrics": _TEMPLATE_OBGYN_PED,
    "ent_oph": _TEMPLATE_ENT,
    "emergency_critical": _TEMPLATE_EMERGENCY,
    "other_clinical": _TEMPLATE_OTHER,
}


# ═══════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════

def get_dept_template(org_id: str, parent_id: str) -> DeptTemplate | None:
    """Get the value stream + BP template for a department."""
    # First check direct mapping
    if org_id in _TEMPLATE_REGISTRY:
        return _TEMPLATE_REGISTRY[org_id]
    # Then check parent group
    if parent_id in _PARENT_TO_TEMPLATE:
        return _PARENT_TO_TEMPLATE[parent_id]
    return _TEMPLATE_OTHER


def get_guideline_info(org_id: str) -> list[dict]:
    """Get known clinical guidelines for a department."""
    return _GUIDELINE_REGISTRY.get(org_id, [])


def get_template_by_type(type_id: str) -> DeptTemplate | None:
    """Get template by dept type name."""
    return _TEMPLATE_REGISTRY.get(type_id, None)


def list_template_types() -> list[str]:
    return list(_TEMPLATE_REGISTRY.keys())
