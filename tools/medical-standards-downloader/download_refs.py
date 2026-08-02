"""Download reference metadata for freely accessible medical standards."""
import json
import time
from datetime import datetime
from pathlib import Path

import requests

OUTPUT = Path(__file__).resolve().parent.parent.parent / "docs" / "standards" / "downloads"
OUTPUT.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers["User-Agent"] = "XHAIP-MedicalStandards/1.0 (academic)"

# Standards to create reference entries for
FREE_STANDARDS = [
    # --- AI Regulatory ---
    ("NMPA-AI-GUIDE", "AI Medical Device Registration Review Guideline 2022",
     "https://www.nmpa.gov.cn/ylqx/ylqxggtg/20220309111021184.html", "regulation"),
    ("CN-AI-GOVERNANCE", "China New Generation AI Governance Principles",
     "https://www.gov.cn/xinwen/2019-06/17/content_5401006.htm", "policy"),
    ("CN-ETHICS-REVIEW", "Science and Technology Ethics Review Measures",
     "https://www.most.gov.cn/xxgk/xinxifenlei/fdzdgknr/fgzc/gfxwj/gfxwj2023/202310/t20231008_188968.html", "regulation"),

    # --- Cardiology ---
    ("ESC-CMP-2023", "2023 ESC Guidelines for Cardiomyopathies",
     "https://academic.oup.com/eurheartj/article/44/37/3503/7246606", "guideline"),
    ("ESC-AFIB-2024", "2024 ESC Guidelines for Atrial Fibrillation",
     "https://academic.oup.com/eurheartj/article/45/36/3314/7738915", "guideline"),
    ("ESC-HF-2021", "2021 ESC Guidelines for Heart Failure",
     "https://academic.oup.com/eurheartj/article/42/36/3599/6358045", "guideline"),
    ("AHA-ACC-HF-2022", "2022 AHA/ACC/HFSA Guideline for HF",
     "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001063", "guideline"),
    ("AHA-ACC-VALVE-2020", "2020 ACC/AHA Valvular Heart Disease Guideline",
     "https://www.ahajournals.org/doi/10.1161/CIR.0000000000000923", "guideline"),
    ("ESC-EACTS-VALVE-2021", "2021 ESC/EACTS Valvular Heart Disease Guideline",
     "https://academic.oup.com/eurheartj/article/43/7/561/6358470", "guideline"),
    ("AHA-ACC-HCM-2020", "2020 AHA/ACC Hypertrophic Cardiomyopathy Guideline",
     "https://www.ahajournals.org/doi/10.1161/CIR.0000000000000937", "guideline"),

    # --- Neurology ---
    ("AHA-ASA-STROKE-2019", "2019 AHA/ASA Acute Ischemic Stroke Guideline",
     "https://www.ahajournals.org/doi/10.1161/STR.0000000000000211", "guideline"),

    # --- Nephrology ---
    ("KDIGO-AKI-2024", "KDIGO 2024 Acute Kidney Injury Guideline",
     "https://kdigo.org/guidelines/acute-kidney-injury/", "guideline"),
    ("KDIGO-CKD-2024", "KDIGO 2024 CKD Evaluation Guideline",
     "https://kdigo.org/guidelines/ckd-evaluation-and-management/", "guideline"),
    ("KDIGO-GN-2024", "KDIGO 2024 Glomerular Diseases Guideline",
     "https://kdigo.org/guidelines/glomerular-diseases/", "guideline"),

    # --- Respiratory ---
    ("GOLD-COPD-2024", "GOLD 2024 Global Strategy for COPD",
     "https://goldcopd.org/2024-gold-report/", "guideline"),
    ("GINA-ASTHMA-2024", "GINA 2024 Global Strategy for Asthma",
     "https://ginasthma.org/2024-report/", "guideline"),

    # --- Endocrinology ---
    ("ADA-DM-2025", "ADA Standards of Care in Diabetes 2025",
     "https://diabetesjournals.org/care/issue/48/Supplement_1", "guideline"),
    ("ESH-HTN-2023", "2023 ESH Guidelines for Hypertension",
     "https://journals.lww.com/jhypertension/fulltext/2023/12000/2023_esh_guidelines_for_the_management_of_arterial.2.aspx", "guideline"),

    # --- Oncology ---
    ("NCCN-BREAST-2025", "NCCN Breast Cancer Guidelines v2.2025",
     "https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1419", "guideline"),
    ("NCCN-GASTRIC-2025", "NCCN Gastric Cancer Guidelines v2.2025",
     "https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1443", "guideline"),
    ("NCCN-COLON-2025", "NCCN Colon Cancer Guidelines v2.2025",
     "https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1428", "guideline"),
    ("ASCO-CHEMO-SAFETY", "ASCO/ONS Chemotherapy Safety Standards",
     "https://ascopubs.org/doi/10.1200/JCO.2016.70.1473", "standard"),

    # --- Orthopedics ---
    ("AAOS-HIP-FX-2021", "AAOS Hip Fractures CPG",
     "https://www.aaos.org/quality/quality-programs/lower-extremity-programs/hip-fractures-in-the-elderly/", "guideline"),
    ("NICE-CG124", "NICE CG124 Hip Fracture Management",
     "https://www.nice.org.uk/guidance/cg124", "guideline"),
    ("SIGN-111", "SIGN 111 Hip Fracture in Older People",
     "https://www.sign.ac.uk/our-guidelines/management-of-hip-fracture-in-older-people/", "guideline"),

    # --- Urology ---
    ("EAU-BLADDER-2026", "EAU Muscle-invasive Bladder Cancer Guideline 2026",
     "https://uroweb.org/guidelines/muscle-invasive-and-metastatic-bladder-cancer", "guideline"),
    ("EAU-PROSTATE-2026", "EAU Prostate Cancer Guideline 2026",
     "https://uroweb.org/guidelines/prostate-cancer", "guideline"),

    # --- Gastroenterology ---
    ("EASL-HCC-2018", "EASL Hepatocellular Carcinoma Guideline",
     "https://www.journal-of-hepatology.eu/article/S0168-8278(18)32150-0/fulltext", "guideline"),
    ("AASLD-HCC-2023", "AASLD Practice Guidance on HCC 2023",
     "https://journals.lww.com/hep/Fulltext/2023/12000/AASLD_Practice_Guidance_on_prevention,_diagnosis,.31.aspx", "guideline"),
    ("ACG-FMT-2023", "ACG Clinical Guideline on Fecal Microbiota Transplantation",
     "https://journals.lww.com/ajg/Fulltext/2023/09000/ACG_Clinical_Guideline_on_Fecal_Microbiota.24.aspx", "guideline"),

    # --- Radiology ---
    ("BI-RADS", "ACR BI-RADS Atlas",
     "https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/Bi-Rads", "standard"),
    ("LI-RADS", "ACR LI-RADS v2018",
     "https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/LI-RADS", "standard"),
    ("Lung-RADS", "ACR Lung-RADS v2022",
     "https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/Lung-Rads", "standard"),
    ("PI-RADS", "ACR PI-RADS v2.1",
     "https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/PI-RADS", "standard"),
    ("ESUR-V10", "ESUR Contrast Agent Guidelines v10",
     "https://www.esur.org/esur-guidelines-on-contrast-agents/", "guideline"),

    # --- Pathology ---
    ("CAP-PROTOCOLS", "CAP Cancer Protocols",
     "https://www.cap.org/protocols-and-guidelines/cancer-reporting-tools/cancer-protocols", "standard"),
    ("ICCR-DATASETS", "ICCR Cancer Reporting Datasets",
     "https://www.iccr-cancer.org/datasets", "standard"),

    # --- Obstetrics/Gynecology ---
    ("FIGO-ENDOMETRIAL-2023", "FIGO Endometrial Cancer Staging 2023",
     "https://obgyn.onlinelibrary.wiley.com/doi/10.1002/ijgo.14930", "classification"),
    ("ESGO-ENDOMETRIAL-2021", "ESGO/ESTRO/ESP Endometrial Cancer Guideline",
     "https://ijgc.bmj.com/content/31/1/12", "guideline"),

    # --- Pediatrics ---
    ("WHO-ENCC", "WHO Essential Newborn Care Course",
     "https://www.who.int/publications/i/item/9789241507884", "guideline"),
    ("ELSO-GUIDELINES", "ELSO Guidelines for ECMO",
     "https://www.elso.org/resources/guidelines.aspx", "guideline"),

    # --- Vascular ---
    ("ESVS-AAA-2024", "ESVS AAA Guidelines 2024",
     "https://www.ejves.com/article/S1078-5884(24)00593-1/fulltext", "guideline"),
    ("ASH-VTE-2020", "ASH 2020 VTE Management Guidelines",
     "https://ashpublications.org/bloodadvances/article/4/19/4693/463998", "guideline"),

    # --- Nutrition ---
    ("ESPEN-GUIDELINES", "ESPEN Clinical Nutrition Guidelines",
     "https://www.espen.org/guidelines-home/espen-guidelines", "guideline"),
    ("ASPEN-GUIDELINES", "ASPEN Clinical Guidelines",
     "https://www.nutritioncare.org/Guidelines_and_Clinical_Resources/", "guideline"),
    ("GLIM-2019", "GLIM Criteria for Malnutrition Diagnosis",
     "https://pubmed.ncbi.nlm.nih.gov/30175482/", "consensus"),

    # --- Infectious Disease ---
    ("IDSA-ASP-2016", "IDSA/SHEA Antibiotic Stewardship Guideline",
     "https://academic.oup.com/cid/article/62/10/e51/2462882", "guideline"),
    ("CDC-AMS-2019", "CDC Core Elements of Hospital Antibiotic Stewardship",
     "https://www.cdc.gov/antibiotic-use/core-elements/hospital.html", "guideline"),
    ("EUCAST-V14", "EUCAST Clinical Breakpoints v14",
     "https://www.eucast.org/clinical_breakpoints", "standard"),

    # --- Pharmacy ---
    ("ASHP-STANDARDS", "ASHP Pharmacy Practice Guidelines",
     "https://www.ashp.org/pharmacy-practice/policy-positions-and-guidelines/browse-by-document-type/guidelines", "standard"),
    ("CPIC-GUIDELINES", "CPIC Pharmacogenomics Guidelines",
     "https://cpicpgx.org/guidelines/", "guideline"),
    ("WFH-HEMOPHILIA", "WFH Hemophilia Management Guidelines 3rd Ed",
     "https://www.wfh.org/en/resources/wfh-treatment-guidelines", "guideline"),

    # --- Management ---
    ("WHO-PATIENT-SAFETY", "WHO Global Patient Safety Action Plan",
     "https://www.who.int/publications/i/item/9789240032705", "framework"),
    ("SQUIRE-2.0", "SQUIRE 2.0 Quality Improvement Reporting",
     "https://www.squire-statement.org/", "guideline"),
    ("ISMP-HIGH-ALERT", "ISMP High-Alert Medications List",
     "https://www.ismp.org/recommendations/high-alert-medications-acute-list", "standard"),

    # --- AI Research Standards ---
    ("CONSORT-AI", "CONSORT-AI Reporting Guideline",
     "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7497823/", "guideline"),
    ("SPIRIT-AI", "SPIRIT-AI Protocol Guideline",
     "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7497824/", "guideline"),
    ("TRIPOD-AI", "TRIPOD+AI Prediction Model Reporting Guideline",
     "https://www.bmj.com/content/385/bmj-2023-078378", "guideline"),
    ("DECIDE-AI", "DECIDE-AI Decision Support Evaluation",
     "https://www.nature.com/articles/s41591-022-01772-9", "guideline"),

    # --- Data Standards ---
    ("FHIR-R4", "HL7 FHIR R4 Specification",
     "https://hl7.org/fhir/R4/", "standard"),
    ("DICOM-3.0", "DICOM Standard 2024",
     "https://www.dicomstandard.org/current", "standard"),
    ("OMOP-CDM", "OMOP Common Data Model v5.4",
     "https://ohdsi.github.io/CommonDataModel/", "standard"),

    # --- WHO ---
    ("WHO-AI-ETHICS", "WHO Ethics and Governance of AI for Health",
     "https://www.who.int/publications/i/item/9789240029200", "framework"),
]

# --- Main ---
manifest = []
total = len(FREE_STANDARDS)
success = 0
failed = 0

print(f"\n{'='*70}")
print("  XHAIP Medical Standards Reference Downloader")
print(f"  Processing {total} standards...")
print(f"{'='*70}\n")

for i, (sid, title, url, stype) in enumerate(FREE_STANDARDS, 1):
    entry = {
        "id": sid, "title": title, "url": url, "type": stype,
        "downloaded": False, "timestamp": datetime.now().isoformat(),
    }

    print(f"  [{i:3d}/{total}] {sid:25s} {title[:50]:50s}", end="")

    try:
        resp = session.get(url, timeout=20, allow_redirects=True)
        if resp.status_code == 200:
            # Save reference file with metadata
            fpath = OUTPUT / f"{sid}-ref.json"
            entry["downloaded"] = True
            entry["status_code"] = resp.status_code
            entry["content_type"] = resp.headers.get("content-type", "")
            entry["final_url"] = resp.url

            fpath.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
            print(" -> OK")
            success += 1
        else:
            entry["status_code"] = resp.status_code
            entry["note"] = f"HTTP {resp.status_code}"
            fpath = OUTPUT / f"{sid}-ref.json"
            fpath.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f" -> HTTP {resp.status_code}")
            failed += 1
    except Exception as e:
        entry["note"] = str(e)[:200]
        fpath = OUTPUT / f"{sid}-ref.json"
        fpath.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f" -> ERR ({str(e)[:40]})")
        failed += 1

    manifest.append(entry)
    time.sleep(0.3)

# Save manifest
manifest_path = OUTPUT / "manifest.json"
manifest_path.write_text(json.dumps({
    "generated": datetime.now().isoformat(),
    "total": total, "success": success, "failed": failed,
    "entries": manifest,
}, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"\n{'='*70}")
print(f"  Summary: {success} accessible, {failed} not reachable")
print(f"  Output: {OUTPUT}")
print(f"  Manifest: {manifest_path}")
print(f"{'='*70}")
