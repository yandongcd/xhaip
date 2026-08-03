# ESPEN 2023 肠外肠内营养指南摘要
# 来源: European Society for Clinical Nutrition and Metabolism
# 状态: 摘要（从临床实践提取核心公式和标准）

name: ESPEN Guidelines on Clinical Nutrition
source: ESPEN (European Society for Clinical Nutrition and Metabolism)
version: 2023
trust_level: T1
category: nutrition

key_content:
  nutritional_screening:
    nrs2002:
      description: 营养风险筛查 (Nutritional Risk Screening 2002)
      components:
        - impaired_nutritional_status: 0-3分 (体重丢失/进食减少/BMI)
        - disease_severity: 0-3分
        - age_bonus: "≥70岁 +1"
      threshold: "≥3分 → 有营养风险, 启动营养干预"
    
    mna_sf:
      description: 老年营养筛查 (Mini Nutritional Assessment - Short Form)
      target: ≥65岁
      scoring: "0-7营养不良 / 8-11有风险 / 12-14正常"

  energy_requirements:
    harris_benedict:
      male: "BEE = 66.5 + 13.75×W(kg) + 5.0×H(cm) - 6.78×A(y)"
      female: "BEE = 655.1 + 9.56×W(kg) + 1.85×H(cm) - 4.68×A(y)"
    stress_factors:
      minor_surgery: 1.1
      major_surgery: 1.3
      sepsis: 1.4
      severe_sepsis: 1.5
      burns_20_40pct: 1.5
      burns_gt_40pct: 2.0

  route_decision:
    EN_preferred: "If gut works, use it — 肠内营养优先"
    PN_indications:
      - "肠梗阻/肠穿孔/严重消化道出血"
      - "短肠综合征(肠内营养不足)"
      - "高流量肠瘘"
    supplemental_PN: "EN不足(摄入<60%目标量超过3天) → 补充性PN"

  tpn_safety:
    calcium_phosphate: "Ca×P <45 (mmol/L)² → 安全; >55 → 高风险沉淀"
    osmolarity_peripheral: "<900 mOsm/L"
    osmolarity_central: ">900 mOsm/L → 必须中心静脉"
    lipid_concentration: "脂肪乳最终浓度 ≥2% (以20%脂肪乳计, 每1000mL≥100mL)"

  refeeding_syndrome:
    risk_factors: "NRS≥5 / BMI<16 / 体重丢失>15%/3月 / 禁食>10天"
    prevention:
      - "初始能量: 10-15 kcal/kg/d (正常需求的25-50%)"
      - "前3天补: 磷+钾+镁+硫胺素200-300mg/d"
      - "每日监测K⁺/Mg²⁺/P (前3天每12h)"
    alert: "P<0.32 mmol/L → 停止营养, 优先补磷"
