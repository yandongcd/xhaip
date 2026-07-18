"""检验危急值智能体 — 检验科首个Agent, 补临床缺口C3.

WS/T 405-2012 临床检验危急值报告与处置规范 + 三甲通行标准.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

CRITICAL_THRESHOLDS: list[dict[str, Any]] = [
    {
        "item": "K+",
        "cn_name": "血清钾",
        "low": 2.5,
        "high": 6.0,
        "unit": "mmol/L",
        "significance": "低钾可致心律失常、呼吸肌麻痹；高钾可致心脏骤停",
        "low_category": "一级危急",
        "high_category": "一级危急",
        "low_note": "补钾+监测ECG",
        "high_note": "钙剂静注+胰岛素+Glucose+血液透析评估",
    },
    {
        "item": "Na+",
        "cn_name": "血清钠",
        "low": 120,
        "high": 160,
        "unit": "mmol/L",
        "significance": "严重低钠可致脑水肿抽搐；高钠可致脑细胞脱水",
        "low_category": "一级危急",
        "high_category": "二级警戒",
        "low_note": "补钠<0.5mmol/L/h防ODS",
        "high_note": "口服或静脉补水",
    },
    {
        "item": "Ca2+",
        "cn_name": "血清钙",
        "low": 1.5,
        "high": 3.5,
        "unit": "mmol/L",
        "significance": "低钙可致手足抽搐、喉痉挛、QT延长；高钙可致心律失常、昏迷",
        "low_category": "一级危急",
        "high_category": "一级危急",
        "low_note": "10%葡萄糖酸钙10ml缓慢静推",
        "high_note": "大量输液+利尿+降钙素",
    },
    {
        "item": "Cl-",
        "cn_name": "血清氯",
        "low": 80,
        "high": 120,
        "unit": "mmol/L",
        "significance": "严重低氯加重代碱；高氯提示高氯性代酸",
        "low_category": "二级警戒",
        "high_category": "二级警戒",
        "low_note": "结合血气综合判断",
        "high_note": "结合血气综合判断",
    },
    {
        "item": "Mg2+",
        "cn_name": "血清镁",
        "low": 0.5,
        "high": 2.5,
        "unit": "mmol/L",
        "significance": "低镁可致心律失常抽搐；高镁可致呼吸抑制",
        "low_category": "一级危急",
        "high_category": "一级危急",
        "low_note": "硫酸镁静注",
        "high_note": "钙剂拮抗+血液透析",
    },
    {
        "item": "Glu",
        "cn_name": "血糖",
        "low": 2.8,
        "high": 22.2,
        "unit": "mmol/L",
        "significance": "严重低血糖可致昏迷脑损伤；高血糖可致DKA/HHS",
        "low_category": "一级危急",
        "high_category": "一级危急",
        "low_note": "50%Glucose 20-40ml静推",
        "high_note": "胰岛素+补液+监测酮体",
    },
    {
        "item": "Hb",
        "cn_name": "血红蛋白",
        "low": 50,
        "high": None,
        "unit": "g/L",
        "significance": "重度贫血可致组织缺氧休克",
        "low_category": "一级危急",
        "high_category": None,
        "low_note": "紧急输注红细胞悬液+排查失血",
        "high_note": None,
    },
    {
        "item": "PLT",
        "cn_name": "血小板",
        "low": 20,
        "high": 1000,
        "unit": "x10_9/L",
        "significance": "PLT<20自发性出血风险；>1000血栓风险",
        "low_category": "一级危急",
        "high_category": "二级警戒",
        "low_note": "输注血小板+排除DIC",
        "high_note": "排查骨髓增殖性疾病",
    },
    {
        "item": "WBC",
        "cn_name": "白细胞",
        "low": 1.0,
        "high": 50,
        "unit": "x10_9/L",
        "significance": "严重白细胞减少有感染风险；显著升高提示严重感染/白血病",
        "low_category": "一级危急",
        "high_category": "一级危急",
        "low_note": "保护性隔离+G-CSF",
        "high_note": "紧急感染排查+血液科会诊",
    },
    {
        "item": "NEUT",
        "cn_name": "中性粒细胞绝对值",
        "low": 0.5,
        "high": None,
        "unit": "x10_9/L",
        "significance": "粒缺有致死性感染风险",
        "low_category": "一级危急",
        "high_category": None,
        "low_note": "保护性隔离+抗感染+血液科急会诊",
        "high_note": None,
    },
    {
        "item": "PT",
        "cn_name": "凝血酶原时间",
        "low": None,
        "high": 30,
        "unit": "s",
        "significance": "PT显著延长提示严重肝损或重度维K缺乏",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "急查肝功+INR+消化科会诊",
    },
    {
        "item": "INR",
        "cn_name": "国际标准化比值",
        "low": None,
        "high": 4.5,
        "unit": "",
        "significance": "INR>4.5大出血风险显著升高",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "停华法林+VitK拮抗+新鲜冰冻血浆",
    },
    {
        "item": "APTT",
        "cn_name": "活化部分凝血活酶时间",
        "low": None,
        "high": 70,
        "unit": "s",
        "significance": "APTT显著延长增加出血风险",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "排查凝血因子缺陷/肝素过量",
    },
    {
        "item": "Fib",
        "cn_name": "纤维蛋白原",
        "low": 1.0,
        "high": None,
        "unit": "g/L",
        "significance": "Fib<1.0提示DIC或严重肝衰竭",
        "low_category": "一级危急",
        "high_category": None,
        "low_note": "输注冷沉淀+DIC全套",
        "high_note": None,
    },
    {
        "item": "cTnI",
        "cn_name": "肌钙蛋白I",
        "low": None,
        "high": 0.5,
        "unit": "ng/mL",
        "significance": "cTnI>0.5 ng/mL为急性心梗报警级",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "启动胸痛绿色通道+ECG+心内科急会诊",
    },
    {
        "item": "CK-MB",
        "cn_name": "肌酸激酶同工酶",
        "low": None,
        "high": 30,
        "unit": "ng/mL",
        "significance": "CK-MB显著升高提示心肌损伤",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "结合cTnI+ECG+心内科会诊",
    },
    {
        "item": "BNP",
        "cn_name": "脑钠肽",
        "low": None,
        "high": 5000,
        "unit": "pg/mL",
        "significance": "极高水平提示急性心衰失代偿",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "心内科急会诊+心脏超声+利尿扩血管",
    },
    {
        "item": "pH",
        "cn_name": "动脉血pH",
        "low": 7.2,
        "high": 7.6,
        "unit": "",
        "significance": "严重酸中毒可致心肌抑制；严重碱中毒可致抽搐痉挛",
        "low_category": "一级危急",
        "high_category": "一级危急",
        "low_note": "排查病因+必要时NaHCO3",
        "high_note": "排查低钾低氯+病因治疗",
    },
    {
        "item": "PaO2",
        "cn_name": "动脉血氧分压",
        "low": 45,
        "high": None,
        "unit": "mmHg",
        "significance": "严重低氧血症可致组织缺氧",
        "low_category": "一级危急",
        "high_category": None,
        "low_note": "高流量给氧+排查ARDS/肺栓塞+呼吸科/ICU",
        "high_note": None,
    },
    {
        "item": "PaCO2",
        "cn_name": "动脉血二氧化碳分压",
        "low": None,
        "high": 70,
        "unit": "mmHg",
        "significance": "严重高碳酸血症致CO2麻醉/意识障碍",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "NIV/气管插管+呼吸科/ICU急会诊",
    },
    {
        "item": "Lac",
        "cn_name": "血乳酸",
        "low": None,
        "high": 4,
        "unit": "mmol/L",
        "significance": "Lac>4为脓毒症休克1h集束化治疗触发值",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "液体复苏+血管活性药+排查感染源+ICU",
    },
    {
        "item": "Cr",
        "cn_name": "血清肌酐",
        "low": None,
        "high": 530,
        "unit": "umol/L",
        "significance": "严重肾功能不全，可能需紧急血液透析",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "肾内科急会诊+评估急诊透析指征",
    },
    {
        "item": "BUN",
        "cn_name": "血尿素氮",
        "low": None,
        "high": 35,
        "unit": "mmol/L",
        "significance": "极高水平提示严重肾衰或高分解状态",
        "low_category": None,
        "high_category": "二级警戒",
        "low_note": None,
        "high_note": "结合Cr+尿量综合评估",
    },
    {
        "item": "血氨",
        "cn_name": "血氨",
        "low": None,
        "high": 100,
        "unit": "umol/L",
        "significance": "显著升高提示肝性脑病危险",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "乳果糖灌肠+BCAA+排查诱因+消化科",
    },
    {
        "item": "TBil新生儿",
        "cn_name": "总胆红素(新生儿)",
        "low": None,
        "high": 342,
        "unit": "umol/L",
        "significance": "核黄疸风险需紧急换血评估",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "光疗+白蛋白+换血准备+新生儿科急会诊",
    },
    {
        "item": "CSF-WBC",
        "cn_name": "脑脊液白细胞",
        "low": None,
        "high": 500,
        "unit": "x10_6/L",
        "significance": "提示CNS感染(化脑/结脑)",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "立即抗感染治疗+神经内科/感染科急会诊",
    },
    {
        "item": "PCT",
        "cn_name": "降钙素原",
        "low": None,
        "high": 10,
        "unit": "ng/mL",
        "significance": "PCT>10强烈提示严重细菌性脓毒症",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "脓毒症集束化治疗+血培养+抗生素+ICU",
    },
    {
        "item": "血淀粉酶",
        "cn_name": "血淀粉酶",
        "low": None,
        "high": 500,
        "unit": "U/L",
        "significance": "血淀粉酶>500U/L提示急性重症胰腺炎",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "禁食水+补液+生长抑素+消化科急会诊+胰腺CT",
    },
    {
        "item": "D-Dimer",
        "cn_name": "D-二聚体",
        "low": None,
        "high": 5000,
        "unit": "ug/L",
        "significance": "极高水平提示DIC或大面积血栓",
        "low_category": None,
        "high_category": "二级警戒",
        "low_note": None,
        "high_note": "结合FDP+DIC积分+影像排除PE/DVT",
    },
    {
        "item": "ALT",
        "cn_name": "谷丙转氨酶",
        "low": None,
        "high": 1000,
        "unit": "U/L",
        "significance": "极高转氨酶提示急性肝坏死/暴发性肝衰",
        "low_category": None,
        "high_category": "一级危急",
        "low_note": None,
        "high_note": "消化科急会诊+肝功能全套+凝血+病毒筛查",
    },
    {
        "item": "Glu新生儿",
        "cn_name": "血糖(新生儿)",
        "low": 2.0,
        "high": 16.7,
        "unit": "mmol/L",
        "significance": "新生儿低血糖可致不可逆脑损伤",
        "low_category": "一级危急",
        "high_category": "一级危急",
        "low_note": "10%Glucose 2ml/kg静推",
        "high_note": "排查先天性糖尿病",
    },
    {
        "item": "K+新生儿",
        "cn_name": "血清钾(新生儿)",
        "low": 3.0,
        "high": 7.0,
        "unit": "mmol/L",
        "significance": "新生儿高钾易致心脏骤停",
        "low_category": "一级危急",
        "high_category": "一级危急",
        "low_note": "参照新生儿K+危急值流程",
        "high_note": "参照新生儿K+危急值流程",
    },
]

DEPT_ROUTE_MAP: dict[str, dict[str, Any]] = {
    "K+": {
        "department": ["肾内科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "Na+": {
        "department": ["肾内科", "ICU", "神经内科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "Ca2+": {
        "department": ["内分泌科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
    "Cl-": {
        "department": ["肾内科"],
        "response_min": 30,
        "escalation": ["值班医生", "科主任"],
    },
    "Mg2+": {
        "department": ["ICU", "肾内科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "Glu": {
        "department": ["内分泌科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
    "Hb": {
        "department": ["输血科", "急诊科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "PLT": {
        "department": ["血液科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
    "WBC": {
        "department": ["血液科", "ICU", "感染科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
    "NEUT": {
        "department": ["血液科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
    "PT": {
        "department": ["消化科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "INR": {
        "department": ["消化科", "心内科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "APTT": {
        "department": ["血液科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
    "Fib": {
        "department": ["ICU", "血液科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "cTnI": {
        "department": ["心内科", "急诊科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
        "special_channel": "胸痛绿色通道",
    },
    "CK-MB": {
        "department": ["心内科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
    "BNP": {
        "department": ["心内科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
    "pH": {
        "department": ["ICU", "呼吸科", "肾内科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "PaO2": {
        "department": ["呼吸科", "ICU", "急诊科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "PaCO2": {
        "department": ["呼吸科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
    "Lac": {
        "department": ["ICU", "急诊科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
        "special_note": "脓毒症1h集束化治疗",
    },
    "Cr": {
        "department": ["肾内科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
    "BUN": {
        "department": ["肾内科"],
        "response_min": 30,
        "escalation": ["值班医生", "科主任"],
    },
    "血氨": {
        "department": ["消化科", "ICU", "肝病科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "TBil新生儿": {
        "department": ["新生儿科", "儿科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "CSF-WBC": {
        "department": ["神经内科", "感染科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "PCT": {
        "department": ["ICU", "感染科", "急诊科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "血淀粉酶": {
        "department": ["消化科", "普外科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
    "D-Dimer": {
        "department": ["呼吸科", "血管外科", "ICU"],
        "response_min": 30,
        "escalation": ["值班医生", "科主任"],
    },
    "ALT": {
        "department": ["消化科", "肝病科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任", "医务处"],
    },
    "Glu新生儿": {
        "department": ["新生儿科", "儿科"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
    "K+新生儿": {
        "department": ["新生儿科", "儿科", "ICU"],
        "response_min": 10,
        "escalation": ["值班医生", "科主任"],
    },
}

_TIMEOUT_MIN: dict[str, int] = {"一级危急": 10, "二级警戒": 30}


def _find_threshold(item: str) -> dict[str, Any] | None:
    for t in CRITICAL_THRESHOLDS:
        if t["item"] == item:
            return t
    return None


def _find_route(item: str) -> dict[str, Any]:
    route = DEPT_ROUTE_MAP.get(item, {})
    if not route:
        return {
            "department": ["急诊科"],
            "response_min": 30,
            "escalation": ["值班医生", "科主任"],
        }
    return route


def check_critical_value(
    item: str = "",
    value: float = 0.0,
    unit: str = "",
    age_group: str = "adult",
    **kwargs: Any,
) -> dict[str, Any]:
    """单项检验危急值判定.

    Args:
        item: 检验项目标识 (如 K+, cTnI, Lac)
        value: 检验数值
        unit: 单位 (用于校验)
        age_group: 年龄分组 (adult/pediatric/neonatal)

    Returns:
        {is_critical, direction, level, significance, review_note, item_info}
    """
    if not item:
        return {"status": "error", "message": "item不能为空", "is_critical": False}

    if not isinstance(value, (int, float)):
        return {"status": "error", "message": "value必须为数值", "is_critical": False}

    threshold = _find_threshold(item)
    if threshold is None:
        return {
            "status": "ok",
            "is_critical": False,
            "item": item,
            "value": value,
            "unit": unit,
            "message": "该项目不在危急值阈值表中",
            "direction": None,
            "level": None,
        }

    low_val = threshold.get("low")
    high_val = threshold.get("high")

    is_critical = False
    direction = None
    level = None
    note = None

    if low_val is not None and value <= low_val:
        is_critical = True
        direction = "低值危急"
        level = threshold.get("low_category")
        note = threshold.get("low_note")

    if high_val is not None and value >= high_val:
        is_critical = True
        direction = "高值危急"
        level = threshold.get("high_category")

    if direction == "高值危急":
        note = threshold.get("high_note")

    if unit and threshold.get("unit") and unit != threshold["unit"]:
        return {
            "status": "error",
            "is_critical": False,
            "item": item,
            "value": value,
            "unit": unit,
            "message": f"单位不匹配: 期望{threshold['unit']}, 实际{unit}",
            "direction": None,
            "level": None,
        }

    if value < (-1e6) or value > 1e12:
        return {
            "status": "error",
            "is_critical": False,
            "item": item,
            "value": value,
            "message": f"数值异常: {value}",
            "direction": None,
            "level": None,
        }

    return {
        "status": "ok",
        "is_critical": is_critical,
        "item": item,
        "cn_name": threshold["cn_name"],
        "value": value,
        "unit": unit or threshold.get("unit", ""),
        "direction": direction,
        "level": level,
        "threshold_low": low_val,
        "threshold_high": high_val,
        "significance": threshold["significance"],
        "review_note": note,
        "age_group": age_group,
    }


def classify_and_route(
    item: str = "",
    value: float = 0.0,
    patient_dept: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """危急值科室路由与升级链推荐.

    Args:
        item: 检验项目标识
        value: 检验数值
        patient_dept: 当前所在科室

    Returns:
        {departments, response_min, escalation, special_channel, check_result}
    """
    check_result = check_critical_value(item=item, value=value)

    if not check_result.get("is_critical"):
        return {
            "status": "ok",
            "is_critical": False,
            "item": item,
            "value": value,
            "message": "非危急值无需路由",
            "departments": [],
            "response_min": None,
            "escalation": [],
        }

    route = _find_route(item)
    departments = list(route.get("department", ["急诊科"]))
    if patient_dept and patient_dept in departments:
        departments.remove(patient_dept)

    return {
        "status": "ok",
        "is_critical": True,
        "item": item,
        "value": value,
        "level": check_result.get("level"),
        "direction": check_result.get("direction"),
        "departments": departments,
        "patient_dept": patient_dept,
        "response_min": route.get("response_min", 30),
        "escalation": route.get("escalation", ["值班医生", "科主任"]),
        "special_channel": route.get("special_channel"),
        "special_note": route.get("special_note"),
        "check_detail": check_result,
    }


def batch_screen(labs: list[dict[str, Any]] | None = None, **kwargs: Any) -> dict[str, Any]:
    """批量检验结果危急值筛查.

    Args:
        labs: [{item, value, unit?, age_group?}, ...]

    Returns:
        {total, hits, misses, hits_by_level}
    """
    if not labs:
        return {"status": "error", "message": "labs不能为空或非列表", "total": 0, "hits": [], "misses": 0}

    try:
        iter(labs)
    except TypeError:
        return {"status": "error", "message": "labs必须为列表", "total": 0, "hits": [], "misses": 0}

    hits: list[dict[str, Any]] = []
    misses: int = 0
    screened: int = 0

    for lab in labs:
        if not isinstance(lab, dict):
            continue
        item = lab.get("item", "")
        value = lab.get("value", 0.0)
        unit = lab.get("unit", "")
        age_group = lab.get("age_group", "adult")

        result = check_critical_value(item=item, value=value, unit=unit, age_group=age_group)
        screened += 1

        if result.get("is_critical"):
            hits.append(result)
        else:
            misses += 1

    hits.sort(key=lambda h: (0 if h.get("level") == "一级危急" else 1, h.get("item", "")))

    return {
        "status": "ok",
        "total_screened": screened,
        "hits_count": len(hits),
        "misses": misses,
        "hits": hits,
        "hits_by_level": _group_by_level(hits),
    }


def _group_by_level(hits: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for h in hits:
        level = h.get("level", "未知")
        result[level] = result.get(level, 0) + 1
    return result


def notification_record(
    item: str = "",
    value: float = 0.0,
    notified_to: str = "",
    ack: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """危急值报告闭环记录.

    Args:
        item: 检验项目
        value: 检验值
        notified_to: 通知接收对象 (科室/姓名)
        ack: 是否已确认

    Returns:
        {record_id, notified_to, ack, timeout, created_at, ...
         为后续LIS订阅与推送落地预留接口形状}
    """
    check_result = check_critical_value(item=item, value=value)

    if not check_result.get("is_critical"):
        return {
            "status": "ok",
            "is_critical": False,
            "item": item,
            "value": value,
            "message": "非危急值无需报告记录",
            "record_id": None,
        }

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    level = check_result.get("level", "二级警戒")
    timeout_minutes = _TIMEOUT_MIN.get(level, 30)
    now_epoch = now.timestamp()

    return {
        "status": "ok",
        "is_critical": True,
        "item": item,
        "cn_name": check_result.get("cn_name", ""),
        "value": value,
        "unit": check_result.get("unit", ""),
        "direction": check_result.get("direction"),
        "level": level,
        "notified_to": notified_to,
        "ack": ack,
        "timeout_minutes": timeout_minutes,
        "timeout": not ack,
        "record_id": f"CV-{now.strftime('%Y%m%d%H%M%S')}-{item}",
        "created_at": now_iso,
        "created_at_epoch": now_epoch,
        "expires_at": now_iso,
        "ack_at": now_iso if ack else None,
        "lis_subscription": {
            "enabled": False,
            "channel": "HL7-ORU-R01",
            "note": "预留LIS接口: 订阅后自动推送危急值报告",
        },
        "push_status": "pending",
        "check_detail": check_result,
    }
