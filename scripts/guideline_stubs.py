"""Step 4: Create guideline YAML stubs for top unmatched citations.
Extracts key content from docs/needs/ where available.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
NEEDS_DIR = ROOT / "docs" / "needs"
GUIDELINES_DIR = ROOT / "packages" / "haip-hospital" / "knowledge" / "guidelines"

# Top citations that need YAML stubs (from analysis)
TOP_MISSING = [
    # Chinese clinical guidelines (high citations)
    ("cma-prostate-cancer-2024", "中国前列腺癌诊疗指南", "clinical", "CUA/CSCO 2024版", 10),
    ("figo-staging-2023", "FIGO 2023 妇科肿瘤分期标准", "clinical", "FIGO 2023", 7),
    ("apache-ii-scoring", "APACHE II 急性生理与慢性健康评分", "scoring", "Knaus et al. 1985", 7),
    ("china-stroke-nutrition-2025", "卒中中心营养支持治疗管理规范(2025版)", "clinical", "中国卒中学会", 5),
    ("eau-urology-2026", "EAU 2026 泌尿外科指南", "clinical", "European Association of Urology", 4),
    ("china-urology-2024", "中国泌尿外科疾病诊断治疗指南(2024)", "clinical", "CUA 2024", 4),
    ("samba-ponv-2020", "SAMBA 术后恶心呕吐管理共识指南", "clinical", "SAMBA 2020", 3),
    ("china-neurogenic-bladder-2023", "神经源性膀胱综合管理临床实践指南", "clinical", "CUA 2023", 3),
    ("china-tumor-quality-2023", "肿瘤诊疗质量提升行动计划", "policy", "国家卫健委 2023", 3),
    ("personal-info-law", "中华人民共和国个人信息保护法", "policy", "全国人大常委会 2021", 3),
    ("china-stroke-nutrition-faq", "卒中营养12问", "clinical", "中国卒中学会", 3),
    ("china-inpatient-glucose-2023", "中国住院患者血糖管理专家共识", "clinical", "中华医学会", 2),
    ("schein-surgical-complications", "Schein外科并发症的预防与处理", "clinical", "Schein 2020", 2),
    ("china-pancreatic-complications-2022", "胰腺术后外科常见并发症防治指南(2022)", "clinical", "CSGO 2022", 2),
    ("china-gi-postop-2018", "中国胃肠肿瘤外科术后并发症诊断登记规范(2018)", "clinical", "CGCA 2018", 2),
    ("china-glaucoma-2025", "中国青光眼诊疗指南(2025版)", "clinical", "中华医学会眼科分会 2025", 2),
    ("esur-contrast-v10", "ESUR对比剂安全指南V10", "clinical", "ESUR V10.0", 2),
    ("clsi-antimicrobial-2024", "CLSI 药敏判读标准(2024)", "lab", "CLSI M100 2024", 2),
    ("data-security-law", "中华人民共和国数据安全法", "policy", "全国人大常委会 2021", 2),
    # International guidelines (frequently cited)
    ("nccn-abdominal-surgery-2024", "NCCN 腹部手术诊疗指南", "clinical", "NCCN 2024", 2),
    ("china-ckd-screening-2022", "中国慢性肾脏病筛查诊断及防治指南", "clinical", "中华医学会肾脏病分会", 1),
    ("china-2dm-2024", "中国2型糖尿病防治指南(2024年版)", "clinical", "中华医学会糖尿病分会 2024", 1),
    ("china-osteoporosis-2022", "中国骨质疏松诊疗指南(2022)", "clinical", "中华医学会骨质疏松分会", 1),
    ("china-glaucoma-consensus-2026", "中国青光眼慢病管理专家共识(2026年)", "clinical", "中华医学会眼科分会 2026", 1),
    ("china-ards-2024", "中国脓毒症/脓毒性休克急诊治疗指南(2024)", "clinical", "SCC中国分会 2024", 1),
    ("china-ra-autoab-2025", "中国类风湿关节炎相关自身抗体临床应用指南(2025版)", "clinical", "中华医学会风湿分会", 1),
    ("china-sle-2025", "中国系统性红斑狼疮诊疗指南(2025版)", "clinical", "中华医学会风湿分会", 1),
    ("china-liver-mdrt-2023", "中国肝癌多学科综合治疗专家共识", "clinical", "中国抗癌协会 2023", 1),
    ("health-medical-data-security", "信息安全技术 健康医疗数据安全指南", "policy", "GB/T 39725-2020", 2),
    ("china-ai-medical-device-2024", "人工智能医疗器械注册审查指导原则", "policy", "NMPA 2024", 1),
]

created = 0
skipped = 0

for stem, name, category, source, ref_count in TOP_MISSING:
    filepath = GUIDELINES_DIR / f"{stem}.yaml"
    if filepath.exists():
        skipped += 1
        continue

    entry = {
        "name": name,
        "category": category,
        "source": source,
        "reference_count": ref_count,
        "trust_level": "T1" if category != "policy" else "T2",
        "status": "baseline-stub",
        "note": f"自动生成于 2026-07-26 | {ref_count}份需求文档引用",
    }

    filepath.write_text(
        yaml.dump(entry, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8"
    )
    created += 1

print(f"Created: {created}, Skipped (exists): {skipped}")

# ── Also check for agents that still need _GUIDELINES ──
print("\n=== Agents still missing _GUIDELINES ===")
AGENTS_DIR = ROOT / "packages" / "haip-hospital" / "agents" / "definitions"
MODULES_DIR = ROOT / "packages" / "haip-hospital" / "modules"

for yf in sorted(AGENTS_DIR.glob("*.yaml")):
    data = yaml.safe_load(yf.read_text(encoding="utf-8"))
    name = data.get("name", "")
    tier = data.get("trust_tier", "standard")
    module_path = MODULES_DIR / name.replace("-", "_")
    init_file = module_path / "__init__.py" if module_path.is_dir() else None

    if init_file and init_file.exists():
        content = init_file.read_text(encoding="utf-8")
        if "_GUIDELINES" not in content and tier in ("deep", "standard"):
            print(f"  MISSING: {name} ({tier})")
    elif not init_file:
        print(f"  NO MODULE: {name} ({tier})")

print("\nDone.")
