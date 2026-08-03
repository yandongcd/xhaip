"""Expand compatible_agents for orphan agents — ensure each agent has ≥10 patients.

Reads patients.json, identifies agents with <10 patient matches, and randomly
assigns patients from semantically matched departments to their compatible_agents.
"""

import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATIENTS_PATH = ROOT / "packages" / "haip-hospital" / "data" / "patients.json"

random.seed(20260727)

# Agent → semantic department mapping (informed by patients_v2.json and medical domain)
# Department names MUST match exact values in patients.json
AGENT_DEPT_MAP: dict[str, list[str]] = {
    "hip-fracture-mdt": ["创伤骨科", "老年病科", "骨科/骨外科", "orthopedic_surgery"],
    "anesthesia": ["创伤骨科", "脊柱骨科", "关节骨科", "普通外科", "肝胆外科",
                   "神经外科", "胸外科", "血管外科", "肾移植科", "烧伤整形科",
                   "介入治疗科", "妇产科", "重症医学科", "整形美容科", "整形美容科",
                   "骨科/骨外科", "cardio_surgery", "orthopedic_surgery", "泌尿外科"],
    "spine-surgery": ["脊柱骨科", "骨科/骨外科", "orthopedic_surgery"],
    "joint-surgery": ["关节骨科", "骨科/骨外科", "orthopedic_surgery"],
    "nurse-general": ["重症医学科", "急诊科"] + [
        "创伤骨科", "脊柱骨科", "关节骨科", "普通外科", "肝胆外科",
        "神经外科", "胸外科", "血管外科", "肾移植科", "烧伤整形科",
        "妇产科", "呼吸内科", "消化内科", "肾内科", "血液内科",
        "内分泌科", "风湿免疫科", "感染内科", "肿瘤科", "骨科/骨外科",
        "pediatrics", "obgyn", "ent"
    ],
    "dietitian": ["重症医学科", "消化内科", "内分泌科", "老年病科", "肾内科", "肿瘤科", "营养科"],
    "emergency-triage": ["急诊科", "急诊医学科"],
    "fall-prevention": ["老年病科", "创伤骨科", "脊柱骨科", "关节骨科", "重症医学科", "口腔科", "骨科/骨外科"],
    "pc-aki": ["心血管内科", "肾内科", "急诊科", "重症医学科", "内分泌科"],
    "pain-management": ["创伤骨科", "脊柱骨科", "关节骨科", "肿瘤科", "骨科/骨外科", "疼痛科", "pain_management"],
    "infection-control": ["重症医学科", "急诊科", "感染内科", "呼吸内科"],
    "sepsis-early-warning": ["重症医学科", "急诊科", "感染内科"],
    "tpn-prescription": ["重症医学科", "消化内科", "营养科"],
    "hypertension-screening": ["心血管内科", "神经外科", "肾内科", "内分泌科", "老年病科", "心血管外科"],
    "cardiovascular-monitor": ["心血管内科", "重症医学科", "急诊科", "心血管外科", "cardio_surgery"],
    "pulmonary-function": ["呼吸内科", "胸外科"],
    "pacer": ["心血管内科", "心血管外科", "急诊科", "重症医学科", "cardio_surgery"],
    "bladder-cancer": ["肿瘤科", "泌尿外科"],
    "breast-imaging": ["乳腺中心", "breast-center"],
    "ahus-detective": ["肾内科", "血液内科"],
    "autoantibody": ["风湿免疫科", "血液内科"],
    "endo-insight": ["消化内科", "肛肠外科"],
    "report-qc": ["呼吸内科", "消化内科", "肿瘤科", "心血管内科", "肾内科", "心血管外科"],
    "drug-agent": [
        "心血管内科", "创伤骨科", "脊柱骨科", "关节骨科", "普通外科", "肝胆外科",
        "神经外科", "胸外科", "急诊科", "重症医学科", "呼吸内科",
        "消化内科", "肾内科", "内分泌科", "肿瘤科", "老年病科", "感染内科"
    ],
    "inf-agent": ["重症医学科", "感染内科", "呼吸内科"],
    "lab-critical-value": ["重症医学科", "急诊科", "心血管内科", "肾内科", "血液内科", "内分泌科"],
    "medical-docs": [
        "创伤骨科", "脊柱骨科", "关节骨科", "普通外科", "肝胆外科",
        "神经外科", "胸外科", "血管外科", "肾移植科", "烧伤整形科",
        "妇产科", "呼吸内科", "消化内科", "肾内科", "骨科/骨外科"
    ],
    "education": ["急诊科", "重症医学科", "神经外科", "心血管内科", "呼吸内科"],
    "voice-health": ["耳鼻喉科", "耳鼻咽喉头颈外科", "ent"],
    "neuro-preconsult": ["神经外科", "急诊科", "神经内科"],
    "elderly-cgm": ["内分泌科", "老年病科", "内分泌代谢科"],
    "mdt": ["创伤骨科", "肿瘤科", "重症医学科", "骨科/骨外科"],
    "togaf": [
        "创伤骨科", "急诊科", "重症医学科", "肿瘤科",
        "呼吸内科", "消化内科", "肾内科", "神经外科", "妇产科",
        "心血管内科", "内分泌科", "感染内科", "血液内科"
    ],
}

TARGET_MIN = 10
TARGET_MAX = 25  # cap to avoid over-concentration


def load_patients_data() -> tuple[list[dict], dict]:
    """Load raw patient data from JSON. Uses the canonical path from haip.patients."""
    from haip.patients import PATIENTS_FILE
    with open(PATIENTS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("patients", []), data


def get_dept_pool(patients: list[dict], dept_names: list[str]) -> list[dict]:
    """Return all patients in given departments that don't already have the agent."""
    return [p for p in patients if p.get("department", "") in dept_names]


def count_agent_coverage(patients: list[dict], agent_name: str) -> int:
    return sum(1 for p in patients if agent_name in p.get("compatible_agents", []))


def main():
    patients, data = load_patients_data()
    print(f"Loaded {len(patients)} patients from patients.json")

    # Build department index
    dept_index: dict[str, list[dict]] = {}
    for p in patients:
        d = p.get("department", "")
        dept_index.setdefault(d, []).append(p)

    # Process each orphan agent
    total_added = 0
    agent_stats: dict[str, dict] = {}

    for agent_name, dept_names in sorted(AGENT_DEPT_MAP.items()):
        current = count_agent_coverage(patients, agent_name)
        # Find matching patients
        pool = get_dept_pool(patients, dept_names)
        # Filter out patients that already have this agent
        pool = [p for p in pool if agent_name not in p.get("compatible_agents", [])]

        needed = max(0, TARGET_MIN - current)
        take = min(needed, len(pool), TARGET_MAX)

        if take == 0:
            agent_stats[agent_name] = {
                "current": current, "available": len(pool), "added": 0,
                "status": "SKIP" if current >= TARGET_MIN else "NO_POOL"
            }
            continue

        selected = random.sample(pool, take)
        for p in selected:
            p["compatible_agents"] = list(p.get("compatible_agents", [])) + [agent_name]

        total_added += take
        agent_stats[agent_name] = {
            "current": current, "available": len(pool), "added": take,
            "status": "OK"
        }

    # ── Report ──
    print(f"\n{'Agent':<30s} {'Before':>6s} {'Added':>6s} {'After':>6s} {'Status':>8s}")
    print("-" * 65)
    for agent_name in sorted(agent_stats):
        s = agent_stats[agent_name]
        after = s["current"] + s["added"]
        print(f"{agent_name:<30s} {s['current']:>6d} {s['added']:>6d} {after:>6d} {s['status']:>8s}")

    no_pool = [a for a, s in agent_stats.items() if s["status"] == "NO_POOL"]
    if no_pool:
        print(f"\nWARNING: {len(no_pool)} agents had no available pool: {no_pool}")

    # ── Write ──
    data["total"] = len(patients)
    data["patients"] = patients
    with open(PATIENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Summary ──
    print(f"\nTotal patients: {len(patients)}")
    print(f"Total compatible_agents assignments added: {total_added}")

    # Coverage summary
    all_agents = Counter()
    for p in patients:
        for a in p.get("compatible_agents", []):
            all_agents[a] += 1

    zero_count = sum(1 for v in all_agents.values() if v == 0)
    under_10 = sum(1 for v in all_agents.values() if 0 < v < 10)
    ok_count = sum(1 for v in all_agents.values() if v >= 10)
    print(f"Agents with >=10 patients: {ok_count}")
    print(f"Agents with 1-9 patients: {under_10}")
    print(f"Agents with 0 patients:  {zero_count}")

    # Top/bottom 5
    print("\nTop 5 agent coverage:")
    for agent, n in all_agents.most_common(5):
        print(f"  {agent:<30s} {n:>6d}")
    print("\nBottom 5 agent coverage:")
    for agent, n in all_agents.most_common()[-5:]:
        print(f"  {agent:<30s} {n:>6d}")


if __name__ == "__main__":
    main()
