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
        "name": "张**", "age": 78, "gender": "女", "diagnosis": "右股骨颈骨折 Garden III",
        "comorbidities": ["高血压", "2型糖尿病"], "medications": ["硝苯地平 30mg qd", "二甲双胍 500mg bid"],
        "allergies": ["青霉素"],
    },
    "P002": {
        "name": "李**", "age": 82, "gender": "男", "diagnosis": "左股骨转子间骨折 Evans ID",
        "comorbidities": ["房颤", "高血压"], "medications": ["华法林 3mg qd", "氨氯地平 5mg qd"],
        "allergies": [],
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


def query_imaging(*, patient_id: str, modality: str = "pelvis_xray",
                  **kwargs: Any) -> dict[str, Any]:
    """Mock PACS 影像查询.

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
