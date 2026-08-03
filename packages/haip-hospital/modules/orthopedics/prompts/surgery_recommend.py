"""Prompt templates for surgery planning and recommendation."""

SYSTEM_PROMPT = """你是一位资深创伤骨科主任医师,专攻老年髋部骨折手术决策.
你需要综合骨折类型, 患者全身状况, 功能需求和预期寿命,
推荐个体化的手术方案,并引用最新临床指南作为依据."""

OUTPUT_SCHEMA = {
    "recommended_surgery": "str — 推荐手术名称",
    "alternative_surgery": "str — 备选手术方案",
    "surgical_approach": "str — 手术入路选择",
    "implant_choice": "str — 内固定物/假体选择建议",
    "anesthesia_recommendation": "str — 麻醉方式建议",
    "key_considerations": "list[str] — 术中关键注意事项",
    "guideline_ref": "str — 引用的指南条款",
    "reasoning": "str — 决策推理过程",
}


def build_prompt(
    diagnosis: str = "",
    fracture_info: str = "",
    age: int | None = None,
    gender: str = "",
    past_history: str = "",
    functional_status: str = "",
    bone_quality: str = "",
    lab_highlights: str = "",
) -> str:
    """Build surgery recommendation prompt."""
    parts = [
        "请为以下患者推荐个体化手术方案:",
        "",
    ]
    if age:
        parts.append(f"年龄: {age}岁")
    if gender:
        parts.append(f"性别: {gender}")
    if diagnosis:
        parts.append(f"诊断: {diagnosis}")
    if fracture_info:
        parts.append(f"骨折信息: {fracture_info}")
    if past_history:
        parts.append(f"既往史: {past_history}")
    if functional_status:
        parts.append(f"功能状态: {functional_status}")
    if bone_quality:
        parts.append(f"骨质量: {bone_quality}")
    if lab_highlights:
        parts.append(f"关键检验: {lab_highlights}")

    parts.extend([
        "",
        "决策需考虑的因素:",
        "1. 骨折类型和稳定性(影响内固定 vs 关节置换选择)",
        "2. 患者年龄和预期寿命",
        "3. 骨质量(骨质疏松程度影响内固定稳定性)",
        "4. 合并症(影响麻醉风险和术后恢复)",
        "5. 活动水平和功能需求",
        "6. 手术时机(48h窗口 vs 延迟手术风险)",
        "",
        "请给出推荐方案并附推理过程.",
    ])
    return "\n".join(parts)
