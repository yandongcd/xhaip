"""Prompt templates for fracture classification and surgery recommendation."""

SYSTEM_PROMPT = """你是一位创伤骨科主治医生,精通AO/OTA骨折分型系统, Garden分型和Evans分型.
请根据影像描述和临床信息,准确判断骨折类型并提供相应的临床建议."""

OUTPUT_SCHEMA = {
    "fracture_type": "str — 骨折类型(如'股骨颈骨折'/'股骨转子间骨折'等)",
    "side": "str — '左侧'/'右侧'/'双侧'",
    "classification_system": "str — 使用的分型系统",
    "classification_type": "str — 具体分型结果",
    "stability": "str — '稳定'/'不稳定'",
    "surgery_recommendation": "str — 手术方案推荐及理由",
    "guideline_ref": "str — 引用的指南依据",
    "confidence": "str — '高'/'中'/'低'",
}


def build_prompt(
    diagnosis: str = "",
    exam_result: str = "",
    age: int | None = None,
    gender: str = "",
    past_history: str = "",
    additional_notes: str = "",
) -> str:
    """Build fracture classification prompt from patient data."""
    parts = [
        "请对以下患者进行骨折分型分析:",
        "",
    ]
    if age:
        parts.append(f"患者年龄: {age}岁")
    if gender:
        parts.append(f"患者性别: {gender}")
    if diagnosis:
        parts.append(f"临床诊断: {diagnosis}")
    if exam_result:
        parts.append(f"影像描述: {exam_result}")
    if past_history:
        parts.append(f"既往史: {past_history}")
    if additional_notes:
        parts.append(f"补充信息: {additional_notes}")

    parts.extend([
        "",
        "请分析:",
        "1. 骨折具体部位和AO/OTA分型",
        "2. Garden分型(股骨颈骨折适用)或Evans分型(转子间骨折适用)",
        "3. 骨折稳定性评估",
        "4. 根据患者年龄和全身状况推荐手术方案",
        "5. 引用相关指南依据(AAOS/NICE/中国指南)",
    ])
    return "\n".join(parts)
