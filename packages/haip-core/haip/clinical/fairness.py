"""患者公平性约束 (MED-4) — 虚拟病人生成的公平性校验.

确保训练/评测数据中疾病×性别×年龄×并发症的分布覆盖代表性组别.
女性心梗症状不同于男性, 罕见病比例不低于真实发病率.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

# ── 性别特异性诊断 (同一疾病, 不同性别表现不同) ──

GENDER_SPECIFIC_PRESENTATIONS: dict[str, dict[str, list[str]]] = {
    "心肌梗死": {
        "M": ["胸痛", "胸闷", "放射痛", "大汗"],
        "F": ["恶心", "疲劳", "上腹痛", "呼吸困难", "头晕"],
    },
    "髋部骨折": {
        "M": ["高能量损伤", "年轻", "运动损伤"],
        "F": ["低能量摔倒", "老年", "骨质疏松"],
    },
}

# ── 罕见病比例约束 (不低于真实发病率) ──

RARE_DISEASE_MIN_RATIO: dict[str, float] = {
    "aHUS (非典型溶血尿毒综合征)": 0.002,   # 2/100000
    "骨髓炎": 0.005,
    "骨肉瘤": 0.001,
    "ANCA相关性血管炎": 0.003,
}

# ── 年龄分层约束 ──

AGE_STRATA = [
    ("青年", 18, 44),
    ("中年", 45, 64),
    ("老年", 65, 79),
    ("高龄", 80, 120),
]


def check_gender_fairness(patients: list[dict[str, Any]]) -> dict[str, Any]:
    """检查性别公平性: 诊断×性别的分布是否均衡."""
    diag_gender = Counter()
    for p in patients:
        dx = str(p.get("diagnosis", ""))
        gender = str(p.get("gender", "")).upper()
        if dx:
            diag_gender[(dx, gender)] += 1

    # 检查性别特异性诊断的覆盖
    gaps = []
    for dx, gendered in GENDER_SPECIFIC_PRESENTATIONS.items():
        m_count = diag_gender.get((dx, "M"), 0)
        f_count = diag_gender.get((dx, "F"), 0)
        if m_count > 0 and f_count == 0:
            gaps.append(f"{dx}: 缺女性患者 (当前{m_count}例男性, 0例女性)")
        elif f_count > 0 and m_count == 0:
            gaps.append(f"{dx}: 缺男性患者 (当前{f_count}例女性, 0例男性)")

    return {
        "total_patients": len(patients),
        "diagnosis_count": len(set(p.get("diagnosis", "") for p in patients)),
        "gender_gaps": gaps,
        "fair": len(gaps) == 0,
    }


def check_age_stratification(patients: list[dict[str, Any]]) -> dict[str, Any]:
    """检查年龄分层: 四个年龄段的患者分布."""
    distribution = {name: 0 for name, _, _ in AGE_STRATA}
    for p in patients:
        age = p.get("age", 0) or 0
        for name, lo, hi in AGE_STRATA:
            if lo <= age <= hi:
                distribution[name] += 1
                break

    total = len(patients)
    return {
        "total": total,
        "strata": {k: round(v / max(1, total) * 100, 1) for k, v in distribution.items()},
        "fair": all(v > 0 for v in distribution.values()),
    }


def check_rare_disease_coverage(patients: list[dict[str, Any]]) -> dict[str, Any]:
    """检查罕见病覆盖: 比例是否不低于真实发病率."""
    dx_count = Counter(p.get("diagnosis", "") for p in patients)
    total = len(patients)
    gaps = []
    for disease, min_ratio in RARE_DISEASE_MIN_RATIO.items():
        actual = dx_count.get(disease, 0) / max(1, total)
        if actual < min_ratio:
            gaps.append(f"{disease}: 当前 {actual:.4f} (需 ≥{min_ratio})")

    return {
        "total": total,
        "rare_disease_gaps": gaps,
        "fair": len(gaps) == 0,
    }


def full_fairness_audit(patients: list[dict[str, Any]]) -> dict[str, Any]:
    """全量公平性审计."""
    gender = check_gender_fairness(patients)
    age = check_age_stratification(patients)
    rare = check_rare_disease_coverage(patients)
    return {
        "gender_fairness": gender,
        "age_stratification": age,
        "rare_disease_coverage": rare,
        "overall_fair": gender["fair"] and age["fair"] and rare["fair"],
        "total_patients": len(patients),
    }
