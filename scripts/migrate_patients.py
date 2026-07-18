r"""Migrate ALL v0.2.0 patient data to xhaip patients.json format.

Covers:
  - synthetic/patients/        — 109 patient dirs (profile + agent_input + admission + ...)
  - clinical/patients/         — 9 clinical NF dirs
  - synthetic/by_department/   — 34 dept JSONs (93 synthetic patients, rich clinical data)
  - indicators/patients/       — 100 time-series lab indicator JSONs
  - synthetic/his_export/      — CSV mapping (MRN → patient_id)
"""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# ─── Configuration ───────────────────────────────────────────────────────────

BASE = ROOT.parent / "haip-0705-2" / "data"
SYNTHETIC_PATIENTS_DIR = BASE / "patients" / "synthetic" / "patients"
CLINICAL_PATIENTS_DIR = BASE / "patients" / "clinical" / "patients"
BY_DEPT_DIR = BASE / "patients" / "synthetic" / "by_department"
INDICATORS_DIR = BASE / "patients" / "indicators" / "patients"
HIS_EXPORT_CSV = BASE / "patients" / "synthetic" / "his_export" / "patients.csv"

TARGET_FILE = ROOT / "packages" / "haip-hospital" / "data" / "patients.json"
ID_PREFIX = "V20-"

# ─── Department → xhaip Agent Mapping ───────────────────────────────────────

DEPARTMENT_TO_AGENTS: dict[str, list[str]] = {
    "中医科": ["tcm"],
    "介入治疗科": ["interventional-therapy"],
    "儿科": ["pediatrics"],
    "内分泌代谢科": ["endocrinology"],
    "口腔科": ["stomatology"],
    "呼吸内科": ["respiratory"],
    "妇产科": ["obgyn"],
    "康复医学科": ["rehabilitation"],
    "心血管内科": ["cardiology"],
    "心血管外科": ["cardio-surgery"],
    "急诊医学科": ["emergency"],
    "感染内科": ["infectious-disease"],
    "普通外科": ["general-surgery"],
    "泌尿外科": ["general-surgery"],
    "消化内科": ["gastroenterology"],
    "烧伤整形外科": ["burns-plastic"],
    "疼痛科": ["pain-hub"],
    "皮肤科": ["dermatology"],
    "眼科": ["ophthalmology"],
    "神经内科": ["neurosurgery"],
    "神经外科": ["neurosurgery"],
    "精神心理科": ["psychiatry"],
    "老年病科": ["geriatrics"],
    "耳鼻咽喉头颈外科": ["ent"],
    "肛肠外科": ["general-surgery"],
    "肝胆外科": ["hepatobiliary-surgery"],
    "肾内科": ["nephrology"],
    "肿瘤科": ["oncology"],
    "胸外科": ["thoracic-surgery"],
    "营养科": ["general-surgery"],
    "血液内科": ["hematology"],
    "血管外科": ["vascular-surgery"],
    "重症医学科": ["icu"],
    "风湿免疫科": ["rheumatology"],
    "骨科/骨外科": ["orthopedic-surgery"],
    "麻醉科": ["anesthesia-risk"],
}

UNIVERSAL_AGENTS = ["medical-record", "pharmacy", "metrics"]
SURGICAL_KEYWORDS = ["外科", "手术", "介入", "麻醉", "移植"]
SURGICAL_AGENTS = ["anesthesia-risk", "cardio-risk"]


def is_surgical(dept_cn: str) -> bool:
    return any(kw in dept_cn for kw in SURGICAL_KEYWORDS)


def build_compatible_agents(dept_cn: str) -> list[str]:
    agents = list(DEPARTMENT_TO_AGENTS.get(dept_cn, ["medical-record"]))
    agents.extend(UNIVERSAL_AGENTS)
    if is_surgical(dept_cn):
        agents.extend(SURGICAL_AGENTS)
    seen = set()
    unique = []
    for a in agents:
        if a not in seen:
            seen.add(a)
            unique.append(a)
    return unique


def gender_map(v02_gender: str) -> str:
    if v02_gender == "男":
        return "M"
    if v02_gender == "女":
        return "F"
    return v02_gender


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_mrn_mapping() -> dict[str, str]:
    """Load MRN → patient_id (Pxxxx) mapping from his_export CSV."""
    mapping: dict[str, str] = {}
    if not HIS_EXPORT_CSV.exists():
        return mapping
    try:
        with open(HIS_EXPORT_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mrn = row.get("mrn", "").strip()
                pid = row.get("patient_id", "").strip()
                if mrn and pid:
                    mapping[mrn] = pid
    except Exception:
        pass
    return mapping


def extract_lab_results(items: list | None) -> dict[str, float]:
    """Extract lab results as a flat {abbr: value} dict."""
    results: dict[str, float] = {}
    if not items:
        return results
    for item in items:
        if isinstance(item, dict):
            abbr = item.get("abbr", "")
            val = item.get("value")
            if abbr and isinstance(val, (int, float)):
                results[abbr] = float(val)
    return results


def extract_lab_results_full(items: list | None) -> list[dict]:
    """Extract lab results as full records (with unit, ref_range, flag)."""
    if not items:
        return []
    return [
        {k: v for k, v in item.items()}
        for item in items
        if isinstance(item, dict)
    ]


# ─── Phase 1: Migrate patient directories ───────────────────────────────────

def convert_patient(pid: str, dir_path: Path) -> dict[str, Any] | None:
    """Convert a single v0.2.0 patient directory to xhaip format."""
    profile = load_json(dir_path / "profile.json")
    if not profile:
        return None

    agent_input = load_json(dir_path / "agent_input.json")
    admission = load_json(dir_path / "admission.json")
    lab_tests_data = load_json(dir_path / "lab_tests.json")
    vitals = load_json(dir_path / "vitals.json")
    examinations = load_json(dir_path / "examinations.json")
    medications = load_json(dir_path / "medications.json")
    clinical = load_json(dir_path / "clinical.json")
    discharge = load_json(dir_path / "discharge_summary.json")

    dept_cn = profile.get("dept_cn", "")
    new_id = f"{ID_PREFIX}{pid}"

    patient: dict[str, Any] = {
        "patient_id": new_id,
        "name": profile.get("name", ""),
        "age": profile.get("age", agent_input.get("age", 0) if agent_input else 0),
        "gender": gender_map(profile.get("gender", "")),
        "department": dept_cn,
        "diagnosis": "",
        "chief_complaint": "",
        "lab_results": {},
        "compatible_agents": build_compatible_agents(dept_cn),
        "source": "v0.2.0_migration",
        "source_id": pid,
    }

    if agent_input:
        patient["diagnosis"] = agent_input.get("diagnosis", "")
        patient["chief_complaint"] = agent_input.get("chief_complaint", "")
        patient["height_cm"] = agent_input.get("height_cm")
        patient["weight_kg"] = agent_input.get("weight_kg")
        patient["present_illness"] = agent_input.get("present_illness", "")
        patient["physical_exam"] = agent_input.get("physical_exam", "")
        patient["past_history"] = agent_input.get("past_history", "")
        patient["allergy_history"] = agent_input.get("allergy_history", "")
        patient["treatment_plan"] = agent_input.get("treatment_plan", "")

    if not patient["diagnosis"] and admission:
        patient["diagnosis"] = admission.get("diagnosis", "")
    if not patient["chief_complaint"] and admission:
        patient["chief_complaint"] = admission.get("chief_complaint", "")

    patient["lab_results"] = extract_lab_results(
        agent_input.get("lab_tests", []) if agent_input else []
    )
    if lab_tests_data and isinstance(lab_tests_data, list):
        extra = extract_lab_results(lab_tests_data)
        for k, v in extra.items():
            if k not in patient["lab_results"]:
                patient["lab_results"][k] = v

    if vitals and isinstance(vitals, dict):
        patient["vitals"] = {str(k): v for k, v in vitals.items()}

    if examinations and isinstance(examinations, list):
        patient["examinations"] = examinations

    if medications and isinstance(medications, list):
        patient["medications"] = medications

    if discharge and isinstance(discharge, dict):
        patient["discharge_summary"] = discharge

    if clinical and isinstance(clinical, dict):
        patient["clinical"] = clinical

    if admission and isinstance(admission, dict):
        patient["admission_date"] = admission.get("admission_date", "")
        patient["discharge_date"] = admission.get("discharge_date", "")
        patient["icd10"] = admission.get("icd10", "")

    return patient


# ─── Phase 2: Enrich from by_department ─────────────────────────────────────

def enrich_from_by_department(
    patients_map: dict[str, dict], mrn_to_pid: dict[str, str]
) -> dict[str, int]:
    """Enrich existing patients with data from by_department JSON files.
    Uses MRN→PID mapping to match patients."""
    stats: dict[str, int] = Counter()
    files_processed = 0

    for entry in sorted(os.listdir(BY_DEPT_DIR)):
        if not entry.endswith(".json"):
            continue
        bd_data = load_json(BY_DEPT_DIR / entry)
        if not bd_data:
            continue

        files_processed += 1
        bd_data.get("dept_name", "")

        for bp in bd_data.get("patients", []):
            mrn = bp.get("mrn", "")
            if not mrn:
                continue  # empty MRN = clinical NF patients, already migrated

            pid = mrn_to_pid.get(mrn, "")
            if not pid:
                continue  # MRN not in CSV mapping

            new_id = f"{ID_PREFIX}{pid}"
            patient = patients_map.get(new_id)
            if not patient:
                continue

            # Enrich treatment_plan
            tp = bp.get("treatment_plan", "")
            if tp and not patient.get("treatment_plan"):
                patient["treatment_plan"] = tp
                stats["treatment_plan_added"] += 1

            # Enrich lab_results with full records
            bd_labs = bp.get("lab_tests", [])
            if bd_labs:
                existing_labs = patient.get("lab_results", {})
                bd_results = extract_lab_results(bd_labs)
                added = 0
                for k, v in bd_results.items():
                    if k not in existing_labs:
                        existing_labs[k] = v
                        added += 1
                if added:
                    stats["lab_results_added"] += added

            # Enrich lab_tests_full (rich format with unit/ref_range/flag)
            if "lab_tests_full" not in patient:
                full = extract_lab_results_full(bd_labs)
                if full:
                    patient["lab_tests_full"] = full
                    stats["lab_tests_full_added"] += 1

    stats["by_department_files"] = files_processed
    return dict(stats)


# ─── Phase 3: Enrich from indicators ────────────────────────────────────────

def enrich_from_indicators(patients_map: dict[str, dict]) -> dict[str, int]:
    """Add time-series lab indicator data to existing patients."""
    stats: dict[str, int] = Counter()
    files_processed = 0

    for entry in sorted(os.listdir(INDICATORS_DIR)):
        if not entry.endswith(".json"):
            continue
        ind_data = load_json(INDICATORS_DIR / entry)
        if not ind_data:
            continue

        files_processed += 1
        pid = ind_data.get("patient_id", "")
        if not pid:
            continue

        new_id = f"{ID_PREFIX}{pid}"
        patient = patients_map.get(new_id)
        if not patient:
            continue

        indicators = ind_data.get("indicators", {})
        if indicators:
            # Merge with existing indicators if any
            existing = patient.get("indicator_trends", {})
            existing.update(indicators)
            patient["indicator_trends"] = existing
            stats["indicator_trends_added"] += 1

            # Also add admission/discharge dates if missing
            if not patient.get("admission_date"):
                patient["admission_date"] = ind_data.get("admission_date", "")
            if not patient.get("discharge_date"):
                patient["discharge_date"] = ind_data.get("discharge_date", "")
            if not patient.get("icd10"):
                patient["icd10"] = ind_data.get("icd10", "")

    stats["indicator_files"] = files_processed
    return dict(stats)


# ─── Phase 4: Count all v0.2.0 data files ───────────────────────────────────

def count_v20_files() -> dict[str, int]:
    """Count all patient data files in v0.2.0 data/."""
    counts: dict[str, int] = {}
    for root, _dirs, files in os.walk(str(BASE)):
        rel = os.path.relpath(root, str(BASE)).replace("\\", "/")
        if rel == ".":
            rel = "data/"
        n = len(files)
        if n > 0:
            counts[rel] = n
    return counts


# ─── Main migration ─────────────────────────────────────────────────────────

def migrate() -> dict[str, Any]:
    """Main migration: full data import from v0.2.0 to xhaip."""

    # 1. Load existing xhaip patients
    existing_patients: list[dict] = []
    if TARGET_FILE.exists():
        existing_data = json.loads(TARGET_FILE.read_text(encoding="utf-8"))
        existing_patients = existing_data.get("patients", [])
        print(f"[1/5] Loaded {len(existing_patients)} existing patients from target")

    patients_map: dict[str, dict] = {p["patient_id"]: p for p in existing_patients}
    existing_ids = set(patients_map.keys())

    # 2. Read patient dirs (synthetic/patients/ + clinical/patients/)
    print("[2/5] Scanning patient directories...")
    v20_patients: list[dict] = []
    dept_stats: Counter = Counter()
    dir_errors: list[str] = []
    dirs_scanned = 0
    dirs_skipped = 0

    for src_dir in [SYNTHETIC_PATIENTS_DIR, CLINICAL_PATIENTS_DIR]:
        if not src_dir.exists():
            continue
        for entry in sorted(os.listdir(src_dir)):
            dir_path = src_dir / entry
            if not dir_path.is_dir():
                continue
            dirs_scanned += 1
            pid = entry
            new_id = f"{ID_PREFIX}{pid}"

            if new_id in existing_ids:
                dirs_skipped += 1
                continue

            patient = convert_patient(pid, dir_path)
            if patient is None:
                dir_errors.append(f"{pid}: could not read profile.json")
                continue

            v20_patients.append(patient)
            patients_map[new_id] = patient
            dept_stats[patient.get("department", "?")] += 1

    # 3. Merge new patients from dirs
    all_patients = existing_patients + v20_patients
    total = len(all_patients)
    print(f"  dirs scanned: {dirs_scanned}, skipped (exists): {dirs_skipped}, "
          f"new: {len(v20_patients)}, errors: {len(dir_errors)}, total: {total}")

    # 4. Enrich from by_department
    print("[3/5] Enriching from by_department data...")
    mrn_mapping = load_mrn_mapping()
    print(f"  MRN→PID mapping: {len(mrn_mapping)} entries")
    bd_stats = enrich_from_by_department(patients_map, mrn_mapping)
    print(f"  by_department files: {bd_stats.get('by_department_files', 0)}, "
          f"treatment_plans added: {bd_stats.get('treatment_plan_added', 0)}, "
          f"lab_results_full added: {bd_stats.get('lab_tests_full_added', 0)}")

    # 5. Enrich from indicators (time-series lab data)
    print("[4/5] Enriching from indicators (time-series lab data)...")
    ind_stats = enrich_from_indicators(patients_map)
    print(f"  indicator files: {ind_stats.get('indicator_files', 0)}, "
          f"indicator_trends added: {ind_stats.get('indicator_trends_added', 0)}")

    # 6. Write output
    print("[5/5] Writing output...")
    all_patients = list(patients_map.values())
    total = len(all_patients)

    output = {"total": total, "patients": all_patients}
    json_str = json.dumps(output, ensure_ascii=False, indent=2)
    TARGET_FILE.write_text(json_str, encoding="utf-8")
    file_size_mb = len(json_str) / (1024 * 1024)

    # 7. Count v0.2.0 files
    file_counts = count_v20_files()
    total_files = sum(file_counts.values())
    json_files = sum(
        n for d, n in file_counts.items() if any(d.startswith(p) for p in [
            "patients/synthetic/patients/",
            "patients/clinical/patients/",
            "patients/synthetic/by_department",
            "patients/synthetic/his_export",
            "patients/indicators/patients",
        ])
    )

    # 8. Report
    print(f"\n{'='*60}")
    print("  Migration Complete")
    print(f"{'='*60}")
    print(f"  Final patient count   : {total}")
    print(f"  Output file size      : {file_size_mb:.1f} MB")
    print(f"  v0.2.0 data files     : {total_files} total, ~{json_files} patient data files")
    print(f"  Patients w/ indicators : {sum(1 for p in all_patients if p.get('indicator_trends'))}")
    print(f"  Patients w/ lab_tests_full: {sum(1 for p in all_patients if p.get('lab_tests_full'))}")

    if dept_stats:
        print("\n  New patients by department:")
        for dept, count in dept_stats.most_common():
            print(f"    {dept}: {count}")

    if dir_errors:
        print("\n  Migration errors:")
        for e in dir_errors:
            print(f"    - {e}")

    return {
        "total": total,
        "migrated": len(v20_patients),
        "enriched_indicators": ind_stats.get("indicator_trends_added", 0),
        "enriched_lab_full": bd_stats.get("lab_tests_full_added", 0),
        "errors": dir_errors,
    }


if __name__ == "__main__":
    migrate()
