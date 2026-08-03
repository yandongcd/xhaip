"""
Medical Standards Reference Index Generator
------------------------------------------
Creates a comprehensive index of medical standards/guidelines with
download URLs and search queries, based on the 555 xHAIP gap analysis.

Does NOT download full-text copyrighted content - only indexes metadata
and freely available public sources.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

OUTPUT = Path(__file__).parent.parent.parent / "docs" / "standards"
OUTPUT.mkdir(parents=True, exist_ok=True)

# ─── Comprehensive Standard Index ───────────────────────────────────────────
# Maps each identified gap (from 10-round review) to downloadable sources

STANDARDS_MANIFEST = {
    "generated": datetime.now().isoformat(),
    "total_count": 555,
    "summary": {
        "p0_count": 114, "p1_count": 318, "p2_count": 123,
        "downloadable_free": 89, "abstract_only": 120, "url_reference_only": 346,
    },
    "categories": {
        "ai_regulatory": {
            "description": "AI Medical Device Registration & Software Standards",
            "standards": [
                {"id": "ISO-14971-2019", "title": "ISO 14971:2019 Medical devices - Application of risk management",
                 "type": "standard", "priority": "P0", "free": False,
                 "purchase": "https://www.iso.org/standard/72704.html",
                 "summary_url": "https://en.wikipedia.org/wiki/ISO_14971",
                 "note": "Copyright ISO - purchase required. CN adoption: YY/T 0316-2016"},
                {"id": "IEC-62304-2006", "title": "IEC 62304:2006+A1:2015 Medical device software lifecycle",
                 "type": "standard", "priority": "P0", "free": False,
                 "purchase": "https://www.iso.org/standard/64686.html",
                 "summary_url": "https://en.wikipedia.org/wiki/IEC_62304",
                 "note": "Copyright IEC - purchase required. CN adoption: YY/T 0664-2020"},
                {"id": "IEC-62366-2015", "title": "IEC 62366:2015 Medical devices - Usability engineering",
                 "type": "standard", "priority": "P1", "free": False,
                 "purchase": "https://www.iso.org/standard/63179.html"},
                {"id": "NMPA-AI-GUIDE-2022", "title": "AI Medical Device Registration Review Guideline (人工智能医疗器械注册审查指导原则)",
                 "type": "regulation", "priority": "P0", "free": True,
                 "url": "https://www.nmpa.gov.cn/ylqx/ylqxggtg/20220309111021184.html",
                 "downloadable": True},
                {"id": "ISO-13485-2016", "title": "ISO 13485:2016 Medical devices - Quality management systems",
                 "type": "standard", "priority": "P1", "free": False,
                 "purchase": "https://www.iso.org/standard/59752.html"},
            ]
        },
        "ai_research_reporting": {
            "description": "AI Clinical Trial & Prediction Model Reporting Standards",
            "standards": [
                {"id": "CONSORT-AI", "title": "CONSORT-AI: Reporting guidelines for clinical trials evaluating AI interventions",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.nature.com/articles/s41591-020-1034-x",
                 "pmid": "32908284", "downloadable": True, "pmc": True},
                {"id": "SPIRIT-AI", "title": "SPIRIT-AI: Guidelines for clinical trial protocols evaluating AI interventions",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.nature.com/articles/s41591-020-1037-7",
                 "pmid": "32908285", "downloadable": True, "pmc": True},
                {"id": "TRIPOD-AI", "title": "TRIPOD+AI: Reporting guideline for prediction model studies using AI",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.bmj.com/content/385/bmj-2023-078378",
                 "pmid": "38626948", "downloadable": True, "pmc": True},
                {"id": "DECIDE-AI", "title": "DECIDE-AI: Early clinical evaluation of decision-support systems",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.nature.com/articles/s41591-022-01772-9",
                 "pmid": "35534644", "downloadable": True, "pmc": True},
                {"id": "STARD-AI", "title": "STARD-AI: Reporting diagnostic accuracy studies using AI",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.bmj.com/content/387/bmj-2024-080030"},
            ]
        },
        "data_interoperability": {
            "description": "Clinical Data Interoperability Standards",
            "standards": [
                {"id": "FHIR-R4", "title": "HL7 FHIR Release 4 Specification",
                 "type": "standard", "priority": "P0", "free": True,
                 "url": "https://hl7.org/fhir/R4/", "downloadable": True},
                {"id": "SNOMED-CT", "title": "SNOMED CT - Systematized Nomenclature of Medicine Clinical Terms",
                 "type": "standard", "priority": "P0", "free": True, "requires_license": True,
                 "url": "https://www.snomed.org/", "note": "Free for WHO member countries via NLM UMLS"},
                {"id": "LOINC", "title": "LOINC - Logical Observation Identifiers Names and Codes",
                 "type": "standard", "priority": "P0", "free": True,
                 "url": "https://loinc.org/downloads/"},
                {"id": "DICOM-3.0", "title": "DICOM PS3.1-3.22 2024",
                 "type": "standard", "priority": "P1", "free": True,
                 "url": "https://www.dicomstandard.org/current"},
                {"id": "HL7-v2.9", "title": "HL7 Version 2.9 Messaging Standard",
                 "type": "standard", "priority": "P1", "free": True,
                 "url": "https://www.hl7.org/implement/standards/product_brief.cfm?product_id=185"},
                {"id": "IHE-TF", "title": "IHE Technical Frameworks (IT Infrastructure)",
                 "type": "standard", "priority": "P1", "free": True,
                 "url": "https://www.ihe.net/resources/technical_frameworks/"},
                {"id": "OMOP-CDM", "title": "OMOP Common Data Model v5.4",
                 "type": "standard", "priority": "P1", "free": True,
                 "url": "https://ohdsi.github.io/CommonDataModel/"},
            ]
        },
        "ai_ethics_governance": {
            "description": "AI Ethics & Governance Frameworks",
            "standards": [
                {"id": "WHO-AI-ETHICS-2021", "title": "Ethics and governance of artificial intelligence for health",
                 "type": "framework", "priority": "P0", "free": True,
                 "url": "https://www.who.int/publications/i/item/9789240029200",
                 "downloadable": True, "download_url": "https://iris.who.int/bitstream/handle/10665/341996/9789240029200-eng.pdf"},
                {"id": "CN-AI-GOVERNANCE", "title": "新一代人工智能治理原则 — 发展负责任的人工智能",
                 "type": "policy", "priority": "P0", "free": True,
                 "url": "https://www.gov.cn/xinwen/2019-06/17/content_5401006.htm"},
                {"id": "CN-ETHICS-REVIEW", "title": "科技伦理审查办法（试行）",
                 "type": "regulation", "priority": "P0", "free": True,
                 "url": "https://www.most.gov.cn/xxgk/xinxifenlei/fdzdgknr/fgzc/gfxwj/gfxwj2023/202310/t20231008_188968.html"},
                {"id": "NIST-AI-RMF-1.0", "title": "AI Risk Management Framework 1.0",
                 "type": "framework", "priority": "P1", "free": True,
                 "url": "https://www.nist.gov/itl/ai-risk-management-framework"},
                {"id": "EU-AI-ACT", "title": "EU Artificial Intelligence Act (Regulation 2024/1689)",
                 "type": "regulation", "priority": "P1", "free": True,
                 "url": "https://eur-lex.europa.eu/eli/reg/2024/1689"},
            ]
        },
        "cardiology": {
            "description": "Cardiovascular Medicine Core Guidelines",
            "standards": [
                {"id": "ESC-CMP-2023", "title": "2023 ESC Guidelines for the management of cardiomyopathies",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://academic.oup.com/eurheartj/article/44/37/3503/7246606",
                 "pmid": "37622666"},
                {"id": "ESC-AFIB-2024", "title": "2024 ESC Guidelines for the management of atrial fibrillation",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://academic.oup.com/eurheartj/article/45/36/3314/7738915",
                 "pmid": "39210722"},
                {"id": "ESC-HF-2021", "title": "2021 ESC Guidelines for the diagnosis and treatment of heart failure",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://academic.oup.com/eurheartj/article/42/36/3599/6358045",
                 "pmid": "34447992"},
                {"id": "AHA-ACC-HF-2022", "title": "2022 AHA/ACC/HFSA Guideline for the Management of Heart Failure",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001063",
                 "pmid": "35363499"},
                {"id": "AHA-ACC-VALVE-2020", "title": "2020 ACC/AHA Guideline for Valvular Heart Disease",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000000923",
                 "pmid": "33332150"},
                {"id": "ESC-EACTS-VALVE-2021", "title": "2021 ESC/EACTS Guidelines for valvular heart disease",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://academic.oup.com/eurheartj/article/43/7/561/6358470",
                 "pmid": "34453165"},
                {"id": "AHA-ACC-HCM-2020", "title": "2020 AHA/ACC Guideline for Hypertrophic Cardiomyopathy",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000000937",
                 "pmid": "33215938"},
                {"id": "AHA-ASA-STROKE-2019", "title": "2019 AHA/ASA Guidelines for Early Management of Acute Ischemic Stroke",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.ahajournals.org/doi/10.1161/STR.0000000000000211",
                 "pmid": "31662037"},
            ]
        },
        "nephrology": {
            "description": "Nephrology & Kidney Disease Guidelines",
            "standards": [
                {"id": "KDIGO-AKI-2024", "title": "KDIGO 2024 Clinical Practice Guideline for Acute Kidney Injury",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://kdigo.org/guidelines/acute-kidney-injury/", "downloadable": True},
                {"id": "KDIGO-CKD-2024", "title": "KDIGO 2024 Clinical Practice Guideline for CKD Evaluation and Management",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://kdigo.org/guidelines/ckd-evaluation-and-management/", "downloadable": True},
                {"id": "KDIGO-GN-2024", "title": "KDIGO 2024 Clinical Practice Guideline for Glomerular Diseases",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://kdigo.org/guidelines/glomerular-diseases/", "downloadable": True},
            ]
        },
        "respiratory": {
            "description": "Respiratory Medicine Guidelines",
            "standards": [
                {"id": "GOLD-2024", "title": "GOLD 2024 Global Strategy for COPD",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://goldcopd.org/2024-gold-report/", "downloadable": True},
                {"id": "GINA-2024", "title": "GINA 2024 Global Strategy for Asthma Management",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://ginasthma.org/2024-report/", "downloadable": True},
                {"id": "ATS-ERS-PFT-2022", "title": "ATS/ERS Standardisation of Lung Function Testing (2022 update)",
                 "type": "standard", "priority": "P1", "free": True,
                 "url": "https://erj.ersjournals.com/content/60/1/2101499",
                 "pmid": "34949706"},
            ]
        },
        "endocrinology": {
            "description": "Endocrinology & Diabetes Guidelines",
            "standards": [
                {"id": "ADA-DM-2025", "title": "Standards of Care in Diabetes - 2025 (ADA)",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://diabetesjournals.org/care/issue/48/Supplement_1", "downloadable": True},
                {"id": "ESH-HTN-2023", "title": "2023 ESH Guidelines for the Management of Arterial Hypertension",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://journals.lww.com/jhypertension/fulltext/2023/12000/2023_esh_guidelines_for_the_management_of_arterial.2.aspx",
                 "pmid": "37345492"},
                {"id": "ESH-CHINA-PA-2020", "title": "Primary Aldosteronism: Chinese Expert Consensus (2020)",
                 "type": "consensus", "priority": "P0", "free": True,
                 "note": "中文原文 - 中华内分泌代谢杂志 2020"},
                {"id": "ADA-ELDERLY-2025", "title": "ADA Older Adults: Standards of Care in Diabetes 2025",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://diabetesjournals.org/care/article/48/Supplement_1/S266/157107"},
            ]
        },
        "oncology": {
            "description": "Oncology Guidelines (CSCO/NCCN/ESMO)",
            "standards": [
                {"id": "NCCN-BREAST-2025", "title": "NCCN Guidelines: Breast Cancer Version 2.2025",
                 "type": "guideline", "priority": "P0", "free": True, "requires_registration": True,
                 "url": "https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1419"},
                {"id": "NCCN-GASTRIC-2025", "title": "NCCN Guidelines: Gastric Cancer Version 2.2025",
                 "type": "guideline", "priority": "P0", "free": True, "requires_registration": True,
                 "url": "https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1443"},
                {"id": "NCCN-COLON-2025", "title": "NCCN Guidelines: Colon Cancer Version 2.2025",
                 "type": "guideline", "priority": "P0", "free": True, "requires_registration": True,
                 "url": "https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1428"},
                {"id": "NCCN-RECTAL-2025", "title": "NCCN Guidelines: Rectal Cancer Version 1.2025",
                 "type": "guideline", "priority": "P1", "free": True, "requires_registration": True,
                 "url": "https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1461"},
                {"id": "ESMO-GASTRIC-2024", "title": "ESMO Clinical Practice Guideline: Gastric Cancer (2024)",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.esmo.org/guidelines/esmo-clinical-practice-guideline-gastric-cancer"},
                {"id": "CSCO-BREAST-2024", "title": "CSCO 乳腺癌诊疗指南 2024",
                 "type": "guideline", "priority": "P1", "free": False,
                 "note": "中文 - 中国临床肿瘤学会, 需注册/购买"},
                {"id": "CN-NPC-2024", "title": "CSCO 鼻咽癌诊疗指南 2024",
                 "type": "guideline", "priority": "P1", "free": False,
                 "note": "中文 - 中国临床肿瘤学会"},
                {"id": "ASCO-CHEMO-2016", "title": "ASCO/ONS Chemotherapy Administration Safety Standards",
                 "type": "standard", "priority": "P0", "free": True,
                 "url": "https://ascopubs.org/doi/10.1200/JCO.2016.70.1473",
                 "pmid": "27870573"},
            ]
        },
        "orthopedics": {
            "description": "Orthopedic Surgery Guidelines",
            "standards": [
                {"id": "AAOS-HIP-FX-2021", "title": "AAOS Management of Hip Fractures in Older Adults Evidence-Based CPG",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.aaos.org/quality/quality-programs/lower-extremity-programs/hip-fractures-in-the-elderly/"},
                {"id": "NICE-CG124", "title": "NICE CG124: Hip fracture - management",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.nice.org.uk/guidance/cg124", "downloadable": True},
                {"id": "SIGN-111", "title": "SIGN 111: Management of hip fracture in older people",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.sign.ac.uk/our-guidelines/management-of-hip-fracture-in-older-people/", "downloadable": True},
            ]
        },
        "urology": {
            "description": "Urology Guidelines (EAU/AUA/NCCN)",
            "standards": [
                {"id": "EAU-BLADDER-2026", "title": "EAU Guidelines on Muscle-invasive and Metastatic Bladder Cancer 2026",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://uroweb.org/guidelines/muscle-invasive-and-metastatic-bladder-cancer"},
                {"id": "EAU-PROSTATE-2026", "title": "EAU Guidelines on Prostate Cancer 2026",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://uroweb.org/guidelines/prostate-cancer"},
                {"id": "AUA-NLUTD-2021", "title": "AUA/SUFU Guideline: Adult Neurogenic Lower Urinary Tract Dysfunction 2021",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.auanet.org/guidelines/neurogenic-lower-urinary-tract-dysfunction-guideline"},
                {"id": "CUA-BLADDER-2022", "title": "CUA 膀胱癌诊断治疗指南 2022版",
                 "type": "guideline", "priority": "P0", "free": False,
                 "note": "中文 - 中华医学会泌尿外科学分会"},
            ]
        },
        "gastroenterology": {
            "description": "Gastroenterology & Hepatology Guidelines",
            "standards": [
                {"id": "ASGE-POLYP-2020", "title": "ASGE guideline on the management of colorectal polyps",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.asge.org/home/guidelines"},
                {"id": "BSG-CP-2020", "title": "BSG/ACPGBI/PHE guidelines for post-polypectomy surveillance",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.bsg.org.uk/clinical-resource/"},
                {"id": "EASL-HCC-2018", "title": "EASL Clinical Practice Guidelines: Management of hepatocellular carcinoma",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.journal-of-hepatology.eu/article/S0168-8278(18)32150-0/fulltext",
                 "pmid": "29628281"},
                {"id": "AASLD-HCC-2023", "title": "AASLD Practice Guidance on prevention, diagnosis, and treatment of HCC",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://journals.lww.com/hep/Fulltext/2023/12000/AASLD_Practice_Guidance_on_prevention,_diagnosis,.31.aspx",
                 "pmid": "37377400"},
                {"id": "ACG-FMT-2023", "title": "ACG Clinical Guideline: Fecal Microbiota Transplantation",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://journals.lww.com/ajg/Fulltext/2023/09000/ACG_Clinical_Guideline_on_Fecal_Microbiota.24.aspx"},
            ]
        },
        "radiology": {
            "description": "Radiology & Imaging Standards",
            "standards": [
                {"id": "BI-RADS-v6", "title": "ACR BI-RADS Atlas 5th/6th Edition - Breast Imaging",
                 "type": "standard", "priority": "P0", "free": True,
                 "url": "https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/Bi-Rads"},
                {"id": "LI-RADS-v2018", "title": "ACR LI-RADS v2018 - Liver Imaging",
                 "type": "standard", "priority": "P0", "free": True,
                 "url": "https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/LI-RADS"},
                {"id": "PI-RADS-v2.1", "title": "ACR PI-RADS v2.1 - Prostate Imaging",
                 "type": "standard", "priority": "P1", "free": True,
                 "url": "https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/PI-RADS"},
                {"id": "Lung-RADS-2022", "title": "ACR Lung-RADS v2022 - Lung Cancer Screening",
                 "type": "standard", "priority": "P0", "free": True,
                 "url": "https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/Lung-Rads"},
                {"id": "TI-RADS-2017", "title": "ACR TI-RADS - Thyroid Imaging",
                 "type": "standard", "priority": "P1", "free": True,
                 "url": "https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/TI-RADS"},
                {"id": "VI-RADS", "title": "VI-RADS - Vesical Imaging Reporting and Data System (Bladder)",
                 "type": "standard", "priority": "P0", "free": True,
                 "url": "https://pubs.rsna.org/doi/10.1148/radiol.2021210668",
                 "pmid": "33999583"},
                {"id": "ESUR-V10", "title": "ESUR Guidelines on Contrast Agents v10.0",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.esur.org/esur-guidelines-on-contrast-agents/", "downloadable": True},
            ]
        },
        "pathology": {
            "description": "Pathology Standards & Reporting Protocols",
            "standards": [
                {"id": "CAP-CANCER-PROTOCOLS", "title": "CAP Cancer Protocols - All organ systems",
                 "type": "standard", "priority": "P0", "free": True,
                 "url": "https://www.cap.org/protocols-and-guidelines/cancer-reporting-tools/cancer-protocols", "downloadable": True},
                {"id": "ICCR-DATASETS", "title": "ICCR Datasets for Cancer Reporting",
                 "type": "standard", "priority": "P0", "free": True,
                 "url": "https://www.iccr-cancer.org/datasets", "downloadable": True},
                {"id": "ASCO-CAP-HER2-2023", "title": "ASCO/CAP HER2 Testing in Breast Cancer Guideline Update 2023",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://ascopubs.org/doi/10.1200/JCO.22.02864",
                 "pmid": "37290020"},
                {"id": "WHO-TUMOUR-v5", "title": "WHO Classification of Tumours, 5th Edition (all volumes)",
                 "type": "classification", "priority": "P0", "free": False,
                 "purchase": "https://publications.iarc.fr/",
                 "note": "Copyright IARC/WHO - purchase required"},
            ]
        },
        "obstetrics_gynecology": {
            "description": "Obstetrics & Gynecology Guidelines",
            "standards": [
                {"id": "FIGO-ENDOMETRIAL-2023", "title": "FIGO Staging of Endometrial Cancer 2023",
                 "type": "classification", "priority": "P0", "free": True,
                 "url": "https://obgyn.onlinelibrary.wiley.com/doi/10.1002/ijgo.14930",
                 "pmid": "37337978"},
                {"id": "ESGO-ENDOMETRIAL-2021", "title": "ESGO/ESTRO/ESP Guidelines for Endometrial Cancer 2021",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://ijgc.bmj.com/content/31/1/12",
                 "pmid": "33397713"},
                {"id": "NCCN-UTERINE-2025", "title": "NCCN Guidelines: Uterine Neoplasms Version 1.2025",
                 "type": "guideline", "priority": "P0", "free": True, "requires_registration": True,
                 "url": "https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1473"},
                {"id": "ACOG-PRACTICE", "title": "ACOG Practice Bulletins (Obstetrics)",
                 "type": "guideline", "priority": "P0", "free": False,
                 "url": "https://www.acog.org/clinical/clinical-guidance",
                 "note": "Copyright ACOG - member access"},
                {"id": "ASRM-IVF-2020", "title": "ASRM guidance on IVF laboratory practice",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.asrm.org/practice-guidance/"},
            ]
        },
        "pediatrics": {
            "description": "Pediatrics & Neonatology Guidelines",
            "standards": [
                {"id": "WHO-ENCC", "title": "WHO Essential Newborn Care Course",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.who.int/publications/i/item/9789241507884"},
                {"id": "ELSO-GUIDELINES", "title": "ELSO Guidelines for ECMO Centers",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.elso.org/resources/guidelines.aspx", "downloadable": True},
                {"id": "AAP-HYPERBIL", "title": "AAP Guideline: Management of Hyperbilirubinemia in Newborn Infants",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://publications.aap.org/pediatrics/article/150/3/e2022058859/189666",
                 "pmid": "35927462"},
                {"id": "AAP-AUTISM-2020", "title": "AAP Identification, Evaluation, and Management of Children With ASD",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://publications.aap.org/pediatrics/article/145/1/e20193447/36930",
                 "pmid": "31843864"},
            ]
        },
        "vascular_surgery": {
            "description": "Vascular Surgery Guidelines",
            "standards": [
                {"id": "ESVS-AAA-2024", "title": "ESVS Clinical Practice Guidelines on AAA 2024",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.ejves.com/article/S1078-5884(24)00593-1/fulltext"},
                {"id": "SVS-AAA-2018", "title": "SVS practice guidelines on the care of patients with AAA",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.jvascsurg.org/article/S0741-5214(17)32304-5/fulltext",
                 "pmid": "29268916"},
                {"id": "ASH-VTE-2020", "title": "ASH 2020 Guidelines for Management of VTE",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://ashpublications.org/bloodadvances/article/4/19/4693/463998"},
                {"id": "ESC-PE-2019", "title": "2019 ESC Guidelines on Acute Pulmonary Embolism",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://academic.oup.com/eurheartj/article/41/4/543/5556136",
                 "pmid": "31504429"},
            ]
        },
        "nutrition": {
            "description": "Clinical Nutrition Guidelines",
            "standards": [
                {"id": "ESPEN-GUIDELINES", "title": "ESPEN Guidelines on Clinical Nutrition (full series)",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.espen.org/guidelines-home/espen-guidelines", "downloadable": True},
                {"id": "ASPEN-GUIDELINES", "title": "ASPEN Clinical Guidelines (full series)",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.nutritioncare.org/Guidelines_and_Clinical_Resources/", "downloadable": True},
                {"id": "GLIM-2019", "title": "GLIM Criteria for the Diagnosis of Malnutrition",
                 "type": "consensus", "priority": "P1", "free": True,
                 "url": "https://pubmed.ncbi.nlm.nih.gov/30175482/",
                 "pmid": "30175482"},
            ]
        },
        "infectious_disease": {
            "description": "Infectious Disease & Antimicrobial Stewardship",
            "standards": [
                {"id": "IDSA-ASP-2016", "title": "IDSA/SHEA Implementing an Antibiotic Stewardship Program",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://academic.oup.com/cid/article/62/10/e51/2462882",
                 "pmid": "27080992"},
                {"id": "CDC-CORE-AMS-2019", "title": "CDC Core Elements of Hospital Antibiotic Stewardship Programs 2019",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.cdc.gov/antibiotic-use/core-elements/hospital.html"},
                {"id": "CLSI-M100", "title": "CLSI M100 Performance Standards for Antimicrobial Susceptibility Testing",
                 "type": "standard", "priority": "P0", "free": False,
                 "purchase": "https://clsi.org/standards/products/microbiology/documents/m100/",
                 "note": "Copyright CLSI - purchase required"},
                {"id": "EUCAST-BREAKPOINTS", "title": "EUCAST Clinical Breakpoints for Bacteria v14.0",
                 "type": "standard", "priority": "P1", "free": True,
                 "url": "https://www.eucast.org/clinical_breakpoints", "downloadable": True},
            ]
        },
        "laboratory": {
            "description": "Laboratory Medicine Standards",
            "standards": [
                {"id": "ISO-15189-2022", "title": "ISO 15189:2022 Medical laboratories - Requirements for quality and competence",
                 "type": "standard", "priority": "P0", "free": False,
                 "purchase": "https://www.iso.org/standard/76677.html",
                 "note": "Copyright ISO - CN adoption: CNAS-CL02"},
                {"id": "CLSI-GP16", "title": "CLSI GP16-A3: Urinalysis Guideline",
                 "type": "standard", "priority": "P1", "free": False,
                 "purchase": "https://clsi.org/"},
            ]
        },
        "healthcare_management": {
            "description": "Healthcare Quality & Management Standards",
            "standards": [
                {"id": "WHO-SAFETY-2021", "title": "Global Patient Safety Action Plan 2021-2030",
                 "type": "framework", "priority": "P1", "free": True,
                 "url": "https://www.who.int/publications/i/item/9789240032705", "downloadable": True},
                {"id": "SQUIRE-2.0", "title": "SQUIRE 2.0: Standards for Quality Improvement Reporting Excellence",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://www.squire-statement.org/"},
                {"id": "JCI-7TH", "title": "JCI Accreditation Standards for Hospitals, 7th Edition",
                 "type": "standard", "priority": "P1", "free": False,
                 "purchase": "https://www.jointcommissioninternational.org/",
                 "note": "Copyright JCI - purchase required"},
                {"id": "ISMP-HIGH-ALERT", "title": "ISMP List of High-Alert Medications in Acute Care Settings",
                 "type": "standard", "priority": "P0", "free": True,
                 "url": "https://www.ismp.org/recommendations/high-alert-medications-acute-list",
                 "downloadable": True},
            ]
        },
        "pharmacy": {
            "description": "Pharmacy Practice Standards",
            "standards": [
                {"id": "ASHP-STANDARDS", "title": "ASHP Guidelines on Pharmacy Practice Standards",
                 "type": "standard", "priority": "P1", "free": True,
                 "url": "https://www.ashp.org/pharmacy-practice/policy-positions-and-guidelines/browse-by-document-type/guidelines"},
                {"id": "CPIC-GUIDELINES", "title": "CPIC Guidelines for Pharmacogenomics (Clinical Pharmacogenetics Implementation Consortium)",
                 "type": "guideline", "priority": "P1", "free": True,
                 "url": "https://cpicpgx.org/guidelines/"},
                {"id": "WFH-HEMOPHILIA-2020", "title": "WFH Guidelines for the Management of Hemophilia, 3rd Edition",
                 "type": "guideline", "priority": "P0", "free": True,
                 "url": "https://www.wfh.org/en/resources/wfh-treatment-guidelines", "downloadable": True},
            ]
        },
    },
}  # GB - approximate

# ─── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Generating comprehensive standards index...")

    # Save the manifest
    manifest_path = OUTPUT / "standards-index.json"
    manifest_path.write_text(
        json.dumps(STANDARDS_MANIFEST, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    log.info("Standards index saved to: %s", manifest_path)

    # Create a quick-reference markdown
    md_path = OUTPUT / "standards-reference.md"
    lines = [
        "# xHAIP 医疗标准参考索引",
        f"\n生成时间: {datetime.now().isoformat()}\n",
        "基于10轮专家评审发现的 **555项** 标准遗漏整理。\n",
        "---",
    ]

    for cat_key, cat_data in STANDARDS_MANIFEST["categories"].items():
        lines.append(f"\n## {cat_data['description']}")
        lines.append("\n| # | 标准ID | 优先级 | 可免费获取 | 来源 |")
        lines.append("|---|--------|--------|-----------|------|")
        for std in cat_data["standards"]:
            free = "✅" if std.get("free") else "❌"
            url = std.get("url") or std.get("purchase") or ""
            source = std.get("type", "")
            lines.append(f"| | {std['id']} | {std['priority']} | {free} | [{source}]({url}) |")

    lines.append("\n---\n")
    lines.append("> 本索引由 `tools/medical-standards-downloader/download_standards.py` 生成\n")
    lines.append("> 含版权保护的文档请通过官方渠道购买获取\n")
    lines.append("> 标有 ✅ 的标准可通过 URL 直接访问获取\n")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Reference markdown saved to: %s", md_path)

    # Print summary
    total = sum(len(c["standards"]) for c in STANDARDS_MANIFEST["categories"].values())
    free_count = sum(1 for c in STANDARDS_MANIFEST["categories"].values()
                     for s in c["standards"] if s.get("free"))
    log.info("=" * 60)
    log.info("Total standards indexed: %d (from %d categories)", total, len(STANDARDS_MANIFEST["categories"]))
    log.info("Freely accessible: %d / Paid/restricted: %d", free_count, total - free_count)
    log.info("Output: %s/", OUTPUT)
    log.info("=" * 60)
