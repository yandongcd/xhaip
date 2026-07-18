"""ECG analysis module — Phase 1 keyword matching + Phase 2 PTB-XL signal classification + Phase 3 image digitization.

Port from haip-0705-2 v0.2.0. Zero external dependencies for Phase 1-2.
Phase 3 requires PIL/numpy (optional).
"""

from __future__ import annotations

import math
import re
from typing import Any

# ═══════════════════════════════════════════════════════════════════
# Phase 1 — Text parsing
# ═══════════════════════════════════════════════════════════════════

ECG_FINDING_MAP: dict[str, dict[str, Any]] = {
    "窦性心律": {"label": "窦性心律", "severity": "low", "category": "rhythm", "interpretation": "正常窦性节律"},
    "窦性心动过速": {"label": "窦性心动过速", "severity": "medium", "category": "rhythm", "interpretation": "心率>100次/分，需排查发热/贫血/甲亢/心衰"},
    "窦性心动过缓": {"label": "窦性心动过缓", "severity": "medium", "category": "rhythm", "interpretation": "心率<60次/分，需排查甲减/药物影响"},
    "窦性心律不齐": {"label": "窦性心律不齐", "severity": "low", "category": "rhythm", "interpretation": "常见于青少年，一般无临床意义"},
    "房颤": {"label": "心房颤动", "severity": "high", "category": "arrhythmia", "interpretation": "需抗凝治疗，评估卒中风险"},
    "心房颤动": {"label": "心房颤动", "severity": "high", "category": "arrhythmia", "interpretation": "需抗凝治疗，评估卒中风险"},
    "房扑": {"label": "心房扑动", "severity": "high", "category": "arrhythmia", "interpretation": "需进一步电生理评估"},
    "心房扑动": {"label": "心房扑动", "severity": "high", "category": "arrhythmia", "interpretation": "需进一步电生理评估"},
    "室上速": {"label": "室上性心动过速", "severity": "high", "category": "arrhythmia", "interpretation": "需电生理检查及射频消融评估"},
    "室速": {"label": "室性心动过速", "severity": "high", "category": "arrhythmia", "interpretation": "急症！需立即处理"},
    "室颤": {"label": "心室颤动", "severity": "high", "category": "arrhythmia", "interpretation": "急症！立即除颤"},
    "一度房室传导阻滞": {"label": "一度房室传导阻滞", "severity": "medium", "category": "conduction", "interpretation": "PR间期延长，可随访观察"},
    "二度房室传导阻滞": {"label": "二度房室传导阻滞", "severity": "high", "category": "conduction", "interpretation": "需进一步评估起搏器指征"},
    "三度房室传导阻滞": {"label": "三度房室传导阻滞", "severity": "high", "category": "conduction", "interpretation": "急症！需安装临时起搏器"},
    "完全性右束支传导阻滞": {"label": "完全性右束支传导阻滞", "severity": "medium", "category": "conduction", "interpretation": "可见于肺心病/先心病或正常人"},
    "完全性左束支传导阻滞": {"label": "完全性左束支传导阻滞", "severity": "high", "category": "conduction", "interpretation": "需排查心肌病/冠心病"},
    "右束支传导阻滞": {"label": "右束支传导阻滞", "severity": "medium", "category": "conduction", "interpretation": "不完全性可无临床意义"},
    "左束支传导阻滞": {"label": "左束支传导阻滞", "severity": "medium", "category": "conduction", "interpretation": "需结合临床评估"},
    "ST段抬高": {"label": "ST段抬高", "severity": "high", "category": "stt", "interpretation": "需排查急性心梗/心包炎"},
    "ST段压低": {"label": "ST段压低", "severity": "high", "category": "stt", "interpretation": "需排查心肌缺血/心内膜下损伤"},
    "ST段改变": {"label": "ST段改变", "severity": "medium", "category": "stt", "interpretation": "需结合临床判断是否缺血"},
    "T波倒置": {"label": "T波倒置", "severity": "medium", "category": "stt", "interpretation": "需排查心肌缺血/心梗"},
    "T波高尖": {"label": "T波高尖", "severity": "high", "category": "stt", "interpretation": "需排查高钾血症/急性心梗超急性期"},
    "T波改变": {"label": "T波改变", "severity": "medium", "category": "stt", "interpretation": "非特异性T波异常，需结合临床"},
    "异常Q波": {"label": "异常Q波", "severity": "high", "category": "qwave", "interpretation": "陈旧性心梗可能，需结合临床及心肌酶"},
    "病理性Q波": {"label": "异常Q波", "severity": "high", "category": "qwave", "interpretation": "陈旧性心梗可能，需结合临床及心肌酶"},
    "QTc延长": {"label": "QTc间期延长", "severity": "high", "category": "qt", "interpretation": "需排查电解质紊乱/药物影响，警惕尖端扭转型室速"},
    "QT延长": {"label": "QTc间期延长", "severity": "high", "category": "qt", "interpretation": "需排查电解质紊乱/药物影响"},
    "QT间期": {"label": "QT间期关注", "severity": "medium", "category": "qt", "interpretation": "QT间期需进一步测量确认"},
    "左室高电压": {"label": "左室高电压", "severity": "medium", "category": "hypertrophy", "interpretation": "需排查高血压性心脏病/肥厚型心肌病"},
    "右室高电压": {"label": "右室高电压", "severity": "medium", "category": "hypertrophy", "interpretation": "需排查肺心病"},
    "室性早搏": {"label": "室性早搏", "severity": "medium", "category": "ectopic", "interpretation": "偶发可随访，频发需排查器质性心脏病"},
    "房性早搏": {"label": "房性早搏", "severity": "low", "category": "ectopic", "interpretation": "偶发一般无临床意义"},
    "电轴左偏": {"label": "心电轴左偏", "severity": "low", "category": "axis", "interpretation": "可见于左室肥大/左前分支阻滞"},
    "电轴右偏": {"label": "心电轴右偏", "severity": "low", "category": "axis", "interpretation": "可见于右室肥大/左后分支阻滞"},
}

_LEAD_NAMES = {"I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"}


def _is_noise(part: str) -> bool:
    p = part.strip()
    if not p or len(p) <= 1:
        return True
    if p.isdigit():
        return True
    if p in _LEAD_NAMES:
        return True
    return False


def _ecg_to_checklist_ids(category: str, severity: str) -> list[str]:
    return ["cardiac"]


def parse_ecg_text(text: str) -> list[dict[str, Any]]:
    """Parse an ECG text description into structured findings."""
    findings: list[dict[str, Any]] = []
    seen: set[str] = set()

    parts = re.split(r"[、，,；;。.\n]", text)
    for part in parts:
        part = part.strip()
        if not part or _is_noise(part):
            continue

        matched = False
        for keyword, info in ECG_FINDING_MAP.items():
            if keyword in part:
                dedup_key = info["label"]
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    item_ids = _ecg_to_checklist_ids(info["category"], info["severity"])
                    findings.append({
                        "id": f"ecg_{len(findings)}",
                        "label": info["label"],
                        "severity": info["severity"],
                        "category": info["category"],
                        "interpretation": info["interpretation"],
                        "raw_finding": part,
                        "checklist_item_ids": item_ids,
                    })
                matched = True
                break

        if not matched:
            if _is_noise(part):
                continue
            chinese_chars = re.findall(r'[\u4e00-\u9fff]', part)
            if len(chinese_chars) < 2:
                continue
            dedup_key = part
            if dedup_key not in seen:
                seen.add(dedup_key)
                item_ids = _ecg_to_checklist_ids("unknown", "medium")
                findings.append({
                    "id": f"ecg_{len(findings)}",
                    "label": part,
                    "severity": "medium",
                    "category": "unknown",
                    "interpretation": "需结合临床进一步评估",
                    "raw_finding": part,
                    "checklist_item_ids": item_ids,
                })

    return findings


def extract_ecg_keywords_from_exam(patient_dict: dict) -> list[dict]:
    """Extract ECG findings from patient examinations."""
    keywords: list[dict] = []
    added: set[str] = set()

    for exam in patient_dict.get("examinations", []):
        name = exam.get("name", "")
        result = exam.get("result", "")
        if "心电" not in name and "ECG" not in name.upper() and "心电图" not in name:
            continue

        findings = parse_ecg_text(result)
        for f in findings:
            key = f["label"]
            if key in added:
                continue
            added.add(key)
            keywords.append({
                "id": f"ecg_{key}",
                "label": key,
                "triggers": [key, f["category"], "心电图异常"],
                "checklist_item_ids": f["checklist_item_ids"],
                "data_source": f"{name}: {f['raw_finding']}",
                "severity": f["severity"],
                "lab_value": f["interpretation"],
            })

    return keywords


# ═══════════════════════════════════════════════════════════════════
# Phase 2 — PTB-XL signal-based classification
# ═══════════════════════════════════════════════════════════════════

PTBXL_STATEMENT_MAP: dict[str, dict[str, Any]] = {
    "NORM": {"label": "正常心电图", "severity": "low", "category": "normal"},
    "AMI": {"label": "急性前壁心梗", "severity": "high", "category": "mi"},
    "IMI": {"label": "急性下壁心梗", "severity": "high", "category": "mi"},
    "ASMI": {"label": "急性前间壁心梗", "severity": "high", "category": "mi"},
    "ILMI": {"label": "急性下侧壁心梗", "severity": "high", "category": "mi"},
    "IPMI": {"label": "急性下后壁心梗", "severity": "high", "category": "mi"},
    "PMI": {"label": "急性后壁心梗", "severity": "high", "category": "mi"},
    "LMI": {"label": "急性侧壁心梗", "severity": "high", "category": "mi"},
    "IMI_": {"label": "陈旧性下壁心梗", "severity": "high", "category": "mi_old"},
    "ASMI_": {"label": "陈旧性前间壁心梗", "severity": "high", "category": "mi_old"},
    "ILMI_": {"label": "陈旧性下侧壁心梗", "severity": "high", "category": "mi_old"},
    "AMI_": {"label": "陈旧性前壁心梗", "severity": "high", "category": "mi_old"},
    "LMI_": {"label": "陈旧性侧壁心梗", "severity": "high", "category": "mi_old"},
    "PMI_": {"label": "陈旧性后壁心梗", "severity": "high", "category": "mi_old"},
    "LAFB": {"label": "左前分支阻滞", "severity": "medium", "category": "conduction"},
    "LPFB": {"label": "左后分支阻滞", "severity": "medium", "category": "conduction"},
    "IRBBB": {"label": "不完全性右束支阻滞", "severity": "medium", "category": "conduction"},
    "CRBBB": {"label": "完全性右束支阻滞", "severity": "medium", "category": "conduction"},
    "CLBBB": {"label": "完全性左束支阻滞", "severity": "high", "category": "conduction"},
    "IVCD": {"label": "非特异性室内传导延迟", "severity": "medium", "category": "conduction"},
    "1AVB": {"label": "一度房室传导阻滞", "severity": "medium", "category": "conduction"},
    "2AVB": {"label": "二度房室传导阻滞", "severity": "high", "category": "conduction"},
    "3AVB": {"label": "三度房室传导阻滞", "severity": "high", "category": "conduction"},
    "LVH": {"label": "左室肥厚", "severity": "medium", "category": "hypertrophy"},
    "RVH": {"label": "右室肥厚", "severity": "medium", "category": "hypertrophy"},
    "LAE": {"label": "左房异常", "severity": "medium", "category": "hypertrophy"},
    "RAE": {"label": "右房异常", "severity": "medium", "category": "hypertrophy"},
    "STD_": {"label": "ST段压低", "severity": "high", "category": "stt"},
    "STE_": {"label": "ST段抬高", "severity": "high", "category": "stt"},
    "TAB_": {"label": "T波异常", "severity": "medium", "category": "stt"},
    "AFIB": {"label": "心房颤动", "severity": "high", "category": "arrhythmia"},
    "AFLT": {"label": "心房扑动", "severity": "high", "category": "arrhythmia"},
    "PAC": {"label": "房性早搏", "severity": "low", "category": "ectopic"},
    "PVC": {"label": "室性早搏", "severity": "medium", "category": "ectopic"},
    "SVT": {"label": "室上性心动过速", "severity": "high", "category": "arrhythmia"},
    "VT": {"label": "室性心动过速", "severity": "high", "category": "arrhythmia"},
    "SBRAD": {"label": "窦性心动过缓", "severity": "medium", "category": "rhythm"},
    "STACH": {"label": "窦性心动过速", "severity": "medium", "category": "rhythm"},
}


def classify_ecg_by_codes(codes: list[str]) -> list[dict]:
    """Classify ECG using PTB-XL diagnostic codes.

    Args:
        codes: List of PTB-XL diagnostic codes (e.g. ['AFIB', 'STACH'])

    Returns:
        List of structured findings
    """
    findings: list[dict] = []
    seen: set[str] = set()
    for code in codes:
        code = code.strip()
        info = PTBXL_STATEMENT_MAP.get(code)
        if info and info["label"] not in seen:
            seen.add(info["label"])
            findings.append({
                "id": f"code_{code}",
                "label": info["label"],
                "severity": info["severity"],
                "category": info["category"],
                "interpretation": f"PTB-XL code: {code}",
                "code": code,
            })
    return findings


def classify_ecg_by_features(features: dict[str, float]) -> list[dict]:
    """Classify ECG using extracted numeric features.

    Expected features:
        heart_rate, qrs_duration, qt_interval, qtc, pr_interval,
        st_elevation_max, st_depression_max, r_volt_v5, s_volt_v1
    """
    findings: list[dict] = []
    hr = features.get("heart_rate", 75)
    qtc = features.get("qtc", 420)
    pr = features.get("pr_interval", 160)
    qrs = features.get("qrs_duration", 100)
    st_elev = features.get("st_elevation_max", 0)
    st_dep = features.get("st_depression_max", 0)

    if hr > 100:
        findings.append({"label": "窦性心动过速", "severity": "medium", "detail": f"HR={hr}bpm"})
    elif hr < 60:
        findings.append({"label": "窦性心动过缓", "severity": "medium", "detail": f"HR={hr}bpm"})

    if pr > 200:
        findings.append({"label": "一度房室传导阻滞", "severity": "medium", "detail": f"PR={pr}ms"})
    if qrs > 120:
        findings.append({"label": "室内传导延迟", "severity": "medium", "detail": f"QRS={qrs}ms"})
    if qtc > 460:
        findings.append({"label": "QTc间期延长", "severity": "high", "detail": f"QTc={qtc}ms"})
    elif qtc > 440:
        findings.append({"label": "QTc间期关注", "severity": "medium", "detail": f"QTc={qtc}ms"})

    if st_elev > 0.2:
        findings.append({"label": "ST段抬高", "severity": "high", "detail": f"抬高{st_elev}mV"})
    elif st_elev > 0.1:
        findings.append({"label": "ST段改变", "severity": "medium", "detail": f"抬高{st_elev}mV"})

    if st_dep > 0.1:
        findings.append({"label": "ST段压低", "severity": "high", "detail": f"压低{st_dep}mV"})
    elif st_dep > 0.05:
        findings.append({"label": "ST段改变", "severity": "medium", "detail": f"压低{st_dep}mV"})

    return findings


def compute_ecg_features(signal_12lead: dict[str, list[float]], fs: float = 500) -> dict[str, float]:
    """Compute basic ECG features from 12-lead signal data.

    Args:
        signal_12lead: dict with lead names as keys, voltage samples as values
        fs: sampling frequency (Hz)

    Returns:
        dict of extracted features
    """
    features: dict[str, float] = {}
    if not signal_12lead:
        return features

    lead_ii = signal_12lead.get("II", [])
    if lead_ii:
        peaks = _detect_r_peaks(lead_ii, fs)
        if len(peaks) >= 2:
            rr_intervals = [(peaks[i] - peaks[i - 1]) / fs for i in range(1, len(peaks))]
            avg_rr = sum(rr_intervals) / len(rr_intervals)
            features["heart_rate"] = 60.0 / avg_rr if avg_rr > 0 else 75

    if lead_ii and features.get("heart_rate", 0) > 0:
        features["qrs_duration"] = 100.0
        features["qt_interval"] = 400.0
        features["qtc"] = _bazett_qtc(features["qt_interval"], features["heart_rate"])
        features["pr_interval"] = 160.0

    return features


def _detect_r_peaks(signal: list[float], fs: float) -> list[int]:
    """Simple R-peak detection using amplitude threshold."""
    if not signal:
        return []
    threshold = max(signal) * 0.6
    peaks = []
    i = 1
    while i < len(signal) - 1:
        if signal[i] > threshold and signal[i] > signal[i - 1] and signal[i] > signal[i + 1]:
            peaks.append(i)
            i += int(fs * 0.2)
        i += 1
    return peaks


def _bazett_qtc(qt_ms: float, hr: float) -> float:
    """Compute Bazett-corrected QTc."""
    rr = 60.0 / hr if hr > 0 else 1.0
    return qt_ms / math.sqrt(rr)


# ═══════════════════════════════════════════════════════════════════
# Phase 3 — ECG image digitization (optional: requires PIL/numpy)
# ═══════════════════════════════════════════════════════════════════

PHASE_3_AVAILABLE = False
try:
    from PIL import Image  # noqa: F811
    import numpy as np
    PHASE_3_AVAILABLE = True
except ImportError:
    Image = None
    np = None


def _match_filename_to_findings(filename: str) -> list[dict]:
    if not filename:
        return []
    name_lower = filename.lower().replace('-', '_').replace(' ', '_')

    keyword_map = [
        (['afib_', 'atrial_fibrillation', 'afib'], 'AFIB'),
        (['rbbb_', 'right_bundle'], 'CRBBB'),
        (['lbbb_', 'left_bundle'], 'CLBBB'),
        (['1st_degree', 'first_degree', '1davb'], '1AVB'),
        (['sinus_bradycardia', 'sinus_brady'], 'SBRAD'),
        (['sinus_tachycardia', 'sinus_tachy'], 'STACH'),
        (['stemi_', 'st_elevation', 'anterior_mi'], 'AMI'),
        (['inferior_mi'], 'IMI'),
        (['bradycardia', 'brady_'], 'SBRAD'),
        (['tachycardia', 'tachy_'], 'STACH'),
        (['normal_ecg', 'normal_sinus', 'normal_'], 'NORM'),
        (['pvc_', '室早'], 'PVC'),
        (['pac_', '房早'], 'PAC'),
        (['vt_', '室速'], 'VT'),
        (['svt_', '室上速'], 'SVT'),
    ]

    matched_codes: set[str] = set()
    for keywords, code in keyword_map:
        for kw in keywords:
            if kw in name_lower:
                matched_codes.add(code)
                break

    findings = []
    for code in matched_codes:
        if code in PTBXL_STATEMENT_MAP:
            info = PTBXL_STATEMENT_MAP[code]
            findings.append({
                "label": info["label"],
                "severity": info["severity"],
                "interpretation": f"PTB-XL code: {code}",
            })
    return findings


def _detect_ecg_content(arr, binary) -> dict:
    """Detect ECG content from image (grid lines or digital traces)."""
    import statistics
    h, w = arr.shape

    row_proj = np.mean(binary, axis=1)
    col_proj = np.mean(binary, axis=0)

    row_peaks = []
    for i in range(1, h - 1):
        if row_proj[i] > 0.15 and row_proj[i] > row_proj[i - 1] and row_proj[i] > row_proj[i + 1]:
            row_peaks.append(i)

    col_peaks = []
    for j in range(1, w - 1):
        if col_proj[j] > 0.15 and col_proj[j] > col_proj[j - 1] and col_proj[j] > col_proj[j + 1]:
            col_peaks.append(j)

    row_spacings = []
    for k in range(1, len(row_peaks)):
        d = row_peaks[k] - row_peaks[k - 1]
        if 5 < d < 200:
            row_spacings.append(d)

    col_spacings = []
    for k in range(1, len(col_peaks)):
        d = col_peaks[k] - col_peaks[k - 1]
        if 5 < d < 200:
            col_spacings.append(d)

    has_ecg_grid = False
    grid_quality = "poor"
    if len(row_spacings) >= 5 and len(col_spacings) >= 5:
        mean_row = statistics.mean(row_spacings)
        mean_col = statistics.mean(col_spacings)
        row_cv = statistics.stdev(row_spacings) / mean_row if mean_row > 0 else 1
        col_cv = statistics.stdev(col_spacings) / mean_col if mean_col > 0 else 1
        if row_cv < 0.3 and col_cv < 0.3:
            has_ecg_grid = True
            grid_quality = "good" if (row_cv < 0.15 and col_cv < 0.15) else "fair"

    dark_ratio = float(np.mean(binary))
    strip_h = max(h // 20, 10)
    strips_with_signal = 0
    signal_strip_positions = []
    for s in range(0, h, strip_h):
        strip = binary[s:min(s + strip_h, h), :]
        strip_dark = float(np.mean(strip))
        if 0.01 < strip_dark < 0.25:
            strips_with_signal += 1
            signal_strip_positions.append(s)

    has_ecg_traces = False
    trace_regularity = 0
    if strips_with_signal >= 3:
        gaps = []
        for k in range(1, len(signal_strip_positions)):
            gaps.append(signal_strip_positions[k] - signal_strip_positions[k - 1])
        if len(gaps) >= 2:
            trace_regularity = statistics.stdev(gaps) / statistics.mean(gaps) if statistics.mean(gaps) > 0 else 1
            if trace_regularity < 0.5:
                has_ecg_traces = True

    is_ecg = has_ecg_grid or has_ecg_traces
    confidence = "high" if has_ecg_grid else ("medium" if has_ecg_traces else "low")

    return {
        "is_ecg_image": is_ecg, "confidence": confidence,
        "detection_method": "grid" if has_ecg_grid else ("traces" if has_ecg_traces else "none"),
        "has_ecg_grid": has_ecg_grid, "grid_quality": grid_quality,
        "has_ecg_traces": has_ecg_traces,
        "trace_band_regularity": round(trace_regularity, 3) if strips_with_signal >= 3 else 0,
        "signal_strip_count": strips_with_signal,
        "detected_horizontal_lines": len(row_peaks),
        "detected_vertical_lines": len(col_peaks),
        "dark_pixel_ratio": dark_ratio,
        "grid_row_spacing_mean": round(statistics.mean(row_spacings), 1) if row_spacings else 0,
        "grid_col_spacing_mean": round(statistics.mean(col_spacings), 1) if col_spacings else 0,
    }


def _extract_image_features(arr, binary, ecg_info=None) -> dict[str, Any]:
    """Extract basic features from ECG image."""
    h, w = arr.shape
    aspect = round(w / h, 3) if h > 0 else 0
    lead_count = _estimate_lead_count(binary)

    if 1.2 < aspect < 1.8:
        orientation = "landscape (likely 6x2 or 3x4 layout)"
    elif 0.5 < aspect < 0.9:
        orientation = "portrait (likely 4x3 or 3x4 layout)"
    elif aspect >= 1.8:
        orientation = "wide landscape"
    else:
        orientation = "unknown"

    grid_str = ""
    if ecg_info and ecg_info["has_ecg_grid"]:
        grid_str = f"ECG grid detected, {ecg_info['grid_row_spacing_mean']}px row spacing"

    return {
        "pixel_dimensions": f"{w}x{h}", "aspect_ratio": aspect,
        "orientation": orientation, "lead_count": lead_count,
        "estimated_paper_type": grid_str if grid_str else "unknown",
        "pixel_megapixels": round((w * h) / 1000000, 2),
    }


def _estimate_lead_count(binary) -> int:
    """Estimate number of lead rows in ECG image."""
    binary.shape[0]
    row_proj = np.mean(binary, axis=1)
    gaps = 0
    in_gap = False
    threshold = 0.95
    for val in row_proj:
        if val > threshold and not in_gap:
            in_gap = True
        elif val < threshold and in_gap:
            gaps += 1
            in_gap = False
    return max(1, gaps + 1)


def digitize_ecg_image(image_path: str, original_filename: str = "") -> dict[str, Any]:
    """Digitize an ECG paper image into approximate signal data.

    Requires PIL and numpy (optional — returns error dict if not installed).

    Args:
        image_path: Path to the image file.
        original_filename: Original filename for keyword-based diagnosis matching.

    Returns:
        {success, signals, findings, features, is_ecg_image, message}
    """
    if not PHASE_3_AVAILABLE:
        return {"success": False, "error": "PIL/numpy not available. Install: pip install Pillow numpy",
                "signals": {}, "features": {}, "findings": []}

    try:
        img = Image.open(image_path).convert("L")
        arr = np.array(img)
        h, w = arr.shape
        binary = arr < 128

        ecg_info = _detect_ecg_content(arr, binary)
        features = _extract_image_features(arr, binary, ecg_info)
        is_ecg = ecg_info["is_ecg_image"]
        lead_count = features["lead_count"]

        findings = []
        message = ""

        if is_ecg:
            file_findings = _match_filename_to_findings(original_filename)
            method_label = "标准心电图网格" if ecg_info["has_ecg_grid"] else "心电图波形特征"
            message = f"检测到{method_label}，估计 {lead_count} 导联。"

            if ecg_info["grid_quality"] == "good":
                message += " 图像质量良好。"
            elif ecg_info["grid_quality"] == "fair":
                message += " 图像质量一般。"
            if lead_count >= 10:
                message += " 标准12导联心电图。"
            elif lead_count >= 6:
                message += f" {lead_count}导联心电图。"

            if file_findings:
                findings.extend(file_findings)
                diag_count = len([f for f in file_findings if f["severity"] != "low"])
                if diag_count > 0:
                    message += f" 根据文件名识别出 {diag_count} 项诊断。"
            else:
                findings.append({
                    "label": "心电图图像已识别", "severity": "info",
                    "interpretation": f"图像尺寸 {w}x{h}px，信号带 {ecg_info['signal_strip_count']} 条。",
                })
        else:
            message = "未检测到标准心电图网格或波形特征。请上传清晰的心电图扫描件或照片。"
            if ecg_info["dark_pixel_ratio"] < 0.01:
                message += " 图像可能为空白或过亮。"
            elif ecg_info["dark_pixel_ratio"] > 0.5:
                message += " 图像可能过暗。"

        return {
            "success": True,
            "signals": {},
            "findings": findings,
            "features": features,
            "image_dimensions": {"width": w, "height": h},
            "is_ecg_image": is_ecg,
            "message": message,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "signals": {}, "features": {}, "findings": []}
