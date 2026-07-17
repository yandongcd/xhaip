"""LIS/HIS/PACS Mock 适配器 — 模拟院内三大业务系统数据查询.

风险缓解 (Risk #7): 内置合理值范围校验，防止 Mock 数据失真影响演示可信度。
所有返回数据标注 _mock: true，可替换为真实 HL7/DICOM 接口。
"""

from __future__ import annotations

from typing import Any

MOCK_LAB_REFERENCE = {
    "cTnI": {"normal": "<0.04", "unit": "ng/mL", "critical_high": 0.5, "range_min": 0.01, "range_max": 5.0},
    "CK-MB": {"normal": "<5.0", "unit": "ng/mL", "critical_high": 30, "range_min": 1.0, "range_max": 50.0},
    "Hb": {"normal": "120-160 (男) / 110-150 (女)", "unit": "g/L", "critical_low": 70, "range_min": 80, "range_max": 170},
    "INR": {"normal": "0.8-1.2", "unit": "", "critical_high": 3.0, "range_min": 0.8, "range_max": 3.0},
    "Cr": {"normal": "44-133", "unit": "μmol/L", "critical_high": 300, "range_min": 40, "range_max": 350},
    "Glu": {"normal": "3.9-6.1", "unit": "mmol/L", "range_min": 2.0, "range_max": 25.0},
}

MOCK_IMAGING = {
    "pelvis_xray": {"view": "骨盆正位", "description": "右股骨颈骨折，Garden III 型，移位约 8mm", "quality": "adequate"},
    "hip_ct": {"view": "髋部 CT 三维重建", "description": "股骨转子间骨折，Evans ID 型，后内侧壁粉碎", "quality": "good"},
}

MOCK_PATIENT_DB = {
    "P001": {
        "name": "张**", "age": 78, "gender": "女",
        "diagnosis": "右股骨颈骨折 Garden III",
        "comorbidities": ["高血压", "2型糖尿病"],
        "medications": ["硝苯地平 30mg qd", "二甲双胍 500mg bid"],
        "allergies": ["青霉素"],
        "labs": {"cTnI": 0.02, "Hb": 95, "Cr": 110, "Glu": 9.5,
                 "WBC": 8.5, "CRP": 40, "INR": 1.1, "egfr": 65},
        "conditions": ["高血压", "糖尿病"],
        "meds": ["nifedipine", "metformin"],
        "fracture_type": "股骨颈骨折", "procedure": "THA (全髋关节置换)",
    },
    "P002": {
        "name": "李**", "age": 82, "gender": "男",
        "diagnosis": "左股骨转子间骨折 Evans ID",
        "comorbidities": ["房颤", "高血压"],
        "medications": ["华法林 3mg qd", "氨氯地平 5mg qd"],
        "allergies": [],
        "labs": {"cTnI": 0.01, "Hb": 138, "Cr": 90, "Glu": 5.4,
                 "WBC": 6.5, "CRP": 6, "INR": 1.1, "egfr": 82},
        "conditions": ["高血压"],
        "meds": ["amlodipine"],
        "fracture_type": "转子间骨折", "procedure": "PFNA (股骨近端防旋髓内钉)",
    },
    "P003": {
        "name": "王**", "age": 80, "gender": "男",
        "diagnosis": "右股骨颈骨折 Garden IV",
        "comorbidities": ["冠心病", "陈旧心梗", "高血压"],
        "medications": ["阿司匹林 100mg qd", "美托洛尔 25mg bid"],
        "allergies": [],
        "labs": {"cTnI": 0.08, "Hb": 105, "Cr": 120, "Glu": 6.8,
                 "WBC": 9.0, "CRP": 30, "INR": 1.2, "egfr": 55},
        "conditions": ["冠心病", "心梗史", "高血压"],
        "meds": ["aspirin", "metoprolol"],
        "fracture_type": "股骨颈骨折", "procedure": "THA (全髋关节置换)",
    },
    "P004": {
        "name": "赵**", "age": 68, "gender": "女",
        "diagnosis": "左股骨转子间骨折 Evans IIA",
        "comorbidities": ["骨质疏松"],
        "medications": ["阿仑膦酸钠 70mg qw"],
        "allergies": [],
        "labs": {"cTnI": 0.01, "Hb": 128, "Cr": 78, "Glu": 5.1,
                 "WBC": 7.0, "CRP": 8, "INR": 1.0, "egfr": 90},
        "conditions": ["骨质疏松"],
        "meds": ["alendronate"],
        "fracture_type": "转子间骨折", "procedure": "PFNA (股骨近端防旋髓内钉)",
    },
    "P005": {
        "name": "陈**", "age": 85, "gender": "女",
        "diagnosis": "右股骨颈骨折 Garden III 合并贫血",
        "comorbidities": ["慢性肾病", "贫血", "痴呆"],
        "medications": ["氯吡格雷 75mg qd"],
        "allergies": ["磺胺"],
        "labs": {"cTnI": 0.03, "Hb": 88, "Cr": 150, "Glu": 6.2,
                 "WBC": 8.0, "CRP": 50, "INR": 1.3, "egfr": 45},
        "conditions": ["慢性肾病", "贫血", "痴呆", "冠心病"],
        "meds": ["clopidogrel"],
        "fracture_type": "股骨颈骨折", "procedure": "THA (全髋关节置换)",
    },
}


def query_labs(*, patient_id: str, lab_items: list[str] | None = None,
               **kwargs: Any) -> dict[str, Any]:
    """Mock LIS 检验数据查询.

    Args:
        patient_id: 患者 ID (P001/P002)
        lab_items: 检验项目列表，为空返回全部

    Returns:
        检验结果，标注 _mock: true
    """
    lab_items = lab_items or list(MOCK_LAB_REFERENCE.keys())
    results = {}

    for item in lab_items:
        ref = MOCK_LAB_REFERENCE.get(item)
        if not ref:
            results[item] = {"error": f"未知检验项目: {item}"}
            continue

        import random
        val = round(random.uniform(ref["range_min"], ref["range_max"]), 2)

        if "critical_high" in ref and val > ref["critical_high"]:
            status = "critical_high"
        elif "critical_low" in ref and val < ref["critical_low"]:
            status = "critical_low"
        else:
            status = "normal"

        results[item] = {"value": val, "unit": ref["unit"], "reference": ref["normal"], "status": status}

    return {
        "patient_id": patient_id,
        "source": "LIS",
        "labs": results,
        "_mock": True,
        "_mock_note": "模拟 LIS 检验数据，检验值在临床合理范围内随机生成",
        "timestamp": "2026-07-11T08:00:00",
    }


def query_patient(*, patient_id: str, **kwargs: Any) -> dict[str, Any]:
    """Mock HIS 患者病历查询.

    Args:
        patient_id: 患者 ID

    Returns:
        患者基本信息 + 诊断 + 合并症 + 用药
    """
    patient = MOCK_PATIENT_DB.get(patient_id, {})
    if not patient:
        return {"patient_id": patient_id, "error": "患者不存在", "_mock": True}

    return {
        **patient,
        "patient_id": patient_id,
        "source": "HIS",
        "_mock": True,
        "_mock_note": "模拟 HIS 病历数据，非真实患者信息",
    }


def list_patient_ids(**kwargs: Any) -> dict[str, Any]:
    """Mock HIS 在册患者 ID 列表 — 前端患者面板的唯一 ID 来源."""
    return {
        "patient_ids": sorted(MOCK_PATIENT_DB.keys()),
        "total": len(MOCK_PATIENT_DB),
        "source": "HIS",
        "_mock": True,
        "_mock_note": "模拟 HIS 在册患者索引",
    }


def query_imaging(*, patient_id: str, modality: str = "pelvis_xray",
                  **kwargs: Any) -> dict[str, Any]:
    """模拟 PACS 影像查询.

    Args:
        patient_id: 患者 ID
        modality: 影像类型 (pelvis_xray / hip_ct)

    Returns:
        影像描述，标注 _mock: true
    """
    img = MOCK_IMAGING.get(modality, {"description": "影像报告待补充", "quality": "unknown"})
    return {
        "patient_id": patient_id,
        "modality": modality,
        "source": "PACS",
        "findings": img,
        "_mock": True,
        "_mock_note": "模拟 PACS 影像报告，非真实 DICOM 数据",
    }
