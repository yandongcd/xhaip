"""Update standards-index.json with missing categories."""
import json
from datetime import datetime
from pathlib import Path

IDX = Path(__file__).resolve().parent.parent.parent / "docs" / "standards" / "standards-index.json"
d = json.loads(IDX.read_text(encoding="utf-8"))

NEW = {
    "neurology_neurosurgery": {
        "description": "Neurology & Neurosurgery Guidelines",
        "standards": [
            {"id":"TOAST-1993","title":"TOAST Classification of Acute Ischemic Stroke Subtypes","type":"classification","priority":"P0","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/7678184/"},
            {"id":"WFNS-SAH","title":"WFNS Grading Scale for SAH","type":"grading","priority":"P0","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/3338060/"},
            {"id":"HUNT-HESS","title":"Hunt-Hess Classification of SAH","type":"grading","priority":"P1","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/"},
            {"id":"WHO-CNS5-2021","title":"WHO Classification of CNS Tumours 5th Ed 2021","type":"classification","priority":"P1","free":True,"url":"https://publications.iarc.fr/","note":"Free online, print purchase"},
            {"id":"ESO-STROKE-2022","title":"ESO Guideline on IV Thrombolysis for AIS 2022","type":"guideline","priority":"P1","free":True,"url":"https://journals.sagepub.com/doi/full/10.1177/23969873221095817"},
            {"id":"CN-NEUROSURGERY-2019","title":"Chinese Neurosurgery Clinical Guidelines (Chinese)","type":"guideline","priority":"P0","free":False,"url":"http://medjournals.cn/","note":"Chinese journal access"},
        ]
    },
    "dermatology": {
        "description": "Dermatology Guidelines",
        "standards": [
            {"id":"NRS-ROSACEA-2019","title":"NRS Updated Classification of Rosacea 2019","type":"classification","priority":"P0","free":True,"url":"https://www.rosacea.org/physicians/classification-of-rosacea"},
            {"id":"AAD-NPF-PSORIASIS-2020","title":"AAD/NPF Joint Guideline for Psoriasis 2020","type":"guideline","priority":"P0","free":True,"url":"https://www.aad.org/member/clinical-quality/guidelines/psoriasis"},
            {"id":"CN-ROSACEA-2021","title":"Chinese Rosacea Guideline 2021","type":"guideline","priority":"P0","free":False,"url":"http://medjournals.cn/","note":"Chinese journal access"},
            {"id":"AAD-ALOPECIA","title":"AAD Alopecia Areata Guideline","type":"guideline","priority":"P1","free":True,"url":"https://www.aad.org/member/clinical-quality/guidelines/alopecia-areata"},
            {"id":"SKINDEX-29","title":"Skindex-29 Dermatology Quality of Life","type":"assessment","priority":"P2","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/9041721/"},
        ]
    },
    "ophthalmology": {
        "description": "Ophthalmology Guidelines",
        "standards": [
            {"id":"AAO-GLAUCOMA-PPP","title":"AAO Preferred Practice Pattern: Primary Open-Angle Glaucoma","type":"guideline","priority":"P0","free":True,"url":"https://www.aao.org/education/preferred-practice-pattern/primary-open-angle-glaucoma-ppp"},
            {"id":"EGS-GLAUCOMA-2023","title":"European Glaucoma Society Guidelines 5th Ed 2023","type":"guideline","priority":"P1","free":True,"url":"https://www.eugs.org/eng/guidelines.asp"},
            {"id":"WGC-GLAUCOMA","title":"World Glaucoma Congress Consensus","type":"consensus","priority":"P1","free":True,"url":"https://www.worldglaucoma.org/"},
            {"id":"CN-GLAUCOMA-2025","title":"Chinese Glaucoma Guideline 2025","type":"guideline","priority":"P0","free":False,"url":"http://medjournals.cn/","note":"Chinese journal access"},
        ]
    },
    "dentistry": {
        "description": "Dentistry / Stomatology Guidelines",
        "standards": [
            {"id":"FDI-NOTATION","title":"FDI Two-Digit Tooth Notation System","type":"standard","priority":"P0","free":True,"url":"https://www.fdiworlddental.org/"},
            {"id":"IAPD-GUIDELINES","title":"IAPD International Paediatric Dentistry Guidelines","type":"guideline","priority":"P1","free":True,"url":"https://iapdworld.org/guidelines/"},
            {"id":"WS506-DENTAL-STERIL","title":"WS 506 Oral Instrument Sterilization Standard","type":"standard","priority":"P0","free":True,"url":"http://www.nhc.gov.cn/","note":"Chinese national standard"},
            {"id":"AO-ASIF-MAXILLOFACIAL","title":"AO/ASIF Maxillofacial Fracture Classification","type":"classification","priority":"P1","free":True,"url":"https://surgeryreference.aofoundation.org/cmf"},
            {"id":"ITI-CONSENSUS","title":"ITI International Team for Implantology Consensus","type":"consensus","priority":"P1","free":True,"url":"https://www.iti.org/","note":"Free for members"},
            {"id":"AAP-PERIO","title":"AAP Periodontal Disease Classification 2018","type":"classification","priority":"P1","free":True,"url":"https://www.perio.org/research-science/"},
            {"id":"CAO-ORTHO","title":"Chinese Orthodontic Clinical Guidelines","type":"guideline","priority":"P1","free":False,"url":"http://www.cndent.com/","note":"Chinese - membership"},
        ]
    },
    "geriatrics": {
        "description": "Geriatrics Guidelines",
        "standards": [
            {"id":"AGS-BEERS-2023","title":"AGS Beers Criteria for PIMs 2023","type":"standard","priority":"P1","free":True,"url":"https://agsjournals.onlinelibrary.wiley.com/doi/10.1111/jgs.18372"},
            {"id":"STOPP-START-v3","title":"STOPP/START Criteria v3 for Prescribing","type":"standard","priority":"P1","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/"},
            {"id":"FRIED-FRAILTY","title":"Fried Frailty Phenotype Criteria","type":"assessment","priority":"P1","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/11253156/"},
            {"id":"CGA-CONSENSUS-CN","title":"Chinese CGA Expert Consensus","type":"consensus","priority":"P0","free":False,"url":"http://medjournals.cn/","note":"Chinese journal access"},
            {"id":"CN-ELDERLY-DM-2024","title":"Chinese Elderly Diabetes Guideline 2024","type":"guideline","priority":"P0","free":False,"url":"http://medjournals.cn/"},
            {"id":"ROCKWOOD-CFS","title":"Rockwood Clinical Frailty Scale","type":"assessment","priority":"P2","free":True,"url":"https://www.dal.ca/sites/gmr/our-tools/clinical-frailty-scale.html"},
        ]
    },
    "emergency_nursing": {
        "description": "Emergency Medicine & Nursing Standards",
        "standards": [
            {"id":"ESI-TRIAGE-v4","title":"ESI Emergency Severity Index v4","type":"standard","priority":"P0","free":True,"url":"https://www.ahrq.gov/patient-safety/settings/emergency-dept/esi.html"},
            {"id":"MEWS-NEWS","title":"NEWS2 National Early Warning Score","type":"assessment","priority":"P1","free":True,"url":"https://www.rcplondon.ac.uk/projects/outputs/national-early-warning-score-news-2"},
            {"id":"CN-CHEST-PAIN-2022","title":"Chinese ACS Emergency Guideline","type":"guideline","priority":"P0","free":False,"url":"http://medjournals.cn/","note":"Chinese journal access"},
            {"id":"BRADEN-SCALE","title":"Braden Scale for Pressure Sore Risk","type":"assessment","priority":"P1","free":True,"url":"https://bradenscale.com/"},
            {"id":"MORSE-FALL","title":"Morse Fall Scale Assessment","type":"assessment","priority":"P1","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/"},
            {"id":"INS-INFUSION-2024","title":"INS Infusion Therapy Standards 2024","type":"standard","priority":"P0","free":False,"purchase":"https://www.ins1.org/","note":"Copyright - purchase"},
            {"id":"CN-NURSING-CAREER-PLAN","title":"China Nursing Career Plan 2021-2025","type":"policy","priority":"P0","free":True,"url":"http://www.nhc.gov.cn/","note":"Free government document"},
            {"id":"JBI-EBN","title":"JBI Evidence-Based Nursing","type":"standard","priority":"P1","free":True,"url":"https://jbi.global/"},
        ]
    },
    "ent_voice": {
        "description": "ENT / Otolaryngology / Voice Guidelines",
        "standards": [
            {"id":"AAO-HNS-VOICE","title":"AAO-HNS CPG: Hoarseness (Dysphonia)","type":"guideline","priority":"P0","free":True,"url":"https://www.entnet.org/quality-products/clinical-practice-guidelines/"},
            {"id":"ELS-VOICE-SURGERY","title":"ELS Phonosurgery Guidelines","type":"guideline","priority":"P1","free":True,"url":"https://www.elsoc.org/"},
            {"id":"CAPE-V","title":"CAPE-V Consensus Auditory-Perceptual Evaluation of Voice","type":"assessment","priority":"P1","free":True,"url":"https://www.asha.org/Form/CAPE-V/"},
            {"id":"ASHA-VOICE-EVAL","title":"ASHA Voice Evaluation Protocol","type":"standard","priority":"P1","free":True,"url":"https://www.asha.org/practice-portal/clinical-topics/voice-disorders/"},
            {"id":"SVHI-10","title":"SVHI-10 Singing Voice Handicap Index","type":"assessment","priority":"P2","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/"},
        ]
    },
    "anesthesiology": {
        "description": "Anesthesiology Guidelines (missing dept in xHAIP)",
        "standards": [
            {"id":"ASA-PHYSICAL-STATUS","title":"ASA Physical Status Classification 2020","type":"classification","priority":"P0","free":True,"url":"https://www.asahq.org/standards-and-practice-parameters/statement-on-asa-physical-status-classification-system"},
            {"id":"ASA-FASTING-2023","title":"ASA Preoperative Fasting Guidelines 2023","type":"guideline","priority":"P0","free":True,"url":"https://www.asahq.org/standards-and-practice-parameters"},
            {"id":"ASA-DIFFICULT-AIRWAY-2022","title":"ASA Difficult Airway Management 2022","type":"guideline","priority":"P1","free":True,"url":"https://pubs.asahq.org/anesthesiology/article/doi/10.1097/ALN.0000000000004002"},
            {"id":"CN-SEDATION-ENDOSCOPY-2019","title":"Chinese Sedation for GI Endoscopy Consensus 2019","type":"consensus","priority":"P0","free":False,"url":"http://medjournals.cn/","note":"Chinese journal access"},
            {"id":"NAP5","title":"NAP5 UK National Audit of Airway Management","type":"standard","priority":"P2","free":True,"url":"https://www.nationalauditprojects.org.uk/NAP5_home"},
        ]
    },
    "scoring_tools": {
        "description": "Scoring & Assessment Tools (cross-disciplinary)",
        "standards": [
            {"id":"CHA2DS2-VASC","title":"CHA2DS2-VASc Stroke Risk in AF","type":"score","priority":"P0","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/28886624/"},
            {"id":"HAS-BLED","title":"HAS-BLED Bleeding Risk Score","type":"score","priority":"P0","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/21036840/"},
            {"id":"MEHRAN-RISK","title":"Mehran Contrast-Induced Nephropathy Risk","type":"score","priority":"P0","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/15216342/"},
            {"id":"WELLS-DVT","title":"Wells Score for DVT Prediction","type":"score","priority":"P1","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/12900679/"},
            {"id":"CHARLSON-CCI","title":"Charlson Comorbidity Index (CCI)","type":"score","priority":"P1","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/3558716/"},
            {"id":"CLAVIEN-DINDO","title":"Clavien-Dindo Surgical Complication Classification","type":"classification","priority":"P1","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/15273542/"},
            {"id":"MASCC-RISK","title":"MASCC Febrile Neutropenia Risk Index","type":"score","priority":"P1","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/10944139/"},
            {"id":"KPS-ECOG","title":"Karnofsky (KPS) / ECOG Performance Status","type":"score","priority":"P1","free":True,"url":"https://ecog-acrin.org/resources/ecog-performance-status/"},
            {"id":"SOFA-SCORE","title":"SOFA Sequential Organ Failure Assessment","type":"score","priority":"P1","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/8844239/"},
            {"id":"APACHE-II","title":"APACHE II Acute Physiology Score","type":"score","priority":"P2","free":True,"url":"https://pubmed.ncbi.nlm.nih.gov/3928249/"},
        ]
    },
    "cn_regulations_ai": {
        "description": "Chinese Medical/AI/Data Regulations",
        "standards": [
            {"id":"CN-MED-DEVICE-REG-2021","title":"Medical Device Supervision Regulations 2021","type":"regulation","priority":"P0","free":True,"url":"https://www.gov.cn/zhengce/content/2021-03/18/content_5593739.htm"},
            {"id":"CN-HUMAN-GENETIC-2019","title":"Human Genetic Resources Regulations","type":"regulation","priority":"P0","free":True,"url":"https://www.gov.cn/zhengce/content/2019-06/10/content_5398829.htm"},
            {"id":"CN-HEALTH-DATA-2018","title":"Health Big Data Standards and Security","type":"regulation","priority":"P0","free":True,"url":"http://www.nhc.gov.cn/","note":"Free government document"},
            {"id":"CN-INTERNET-MEDICAL","title":"Internet Medical Treatment Measures","type":"regulation","priority":"P1","free":True,"url":"http://www.nhc.gov.cn/"},
            {"id":"YYT-1833-2022","title":"YY/T 1833-2022 AI Medical Device Dataset Requirements","type":"standard","priority":"P1","free":False,"url":"https://www.nmpa.gov.cn/","note":"Industry standard"},
            {"id":"YYT-1843-2022","title":"YY/T 1843-2022 AI Medical Device Quality Requirements","type":"standard","priority":"P1","free":False,"url":"https://www.nmpa.gov.cn/","note":"Industry standard"},
        ]
    },
    "p2_advanced": {
        "description": "P2 Advanced Standards & Frameworks",
        "standards": [
            {"id":"MODEL-CARD","title":"Model Cards for Model Reporting","type":"standard","priority":"P2","free":True,"url":"https://arxiv.org/abs/1810.03993"},
            {"id":"PRO-CTCAE","title":"PRO-CTCAE Patient-Reported Outcomes","type":"standard","priority":"P2","free":True,"url":"https://healthcaredelivery.cancer.gov/pro-ctcae/"},
            {"id":"ICHOM-STANDARDS","title":"ICHOM Standard Sets for Patient Outcomes","type":"standard","priority":"P2","free":True,"url":"https://www.ichom.org/standard-sets/"},
            {"id":"CHEERS-2022","title":"CHEERS 2022 Health Economic Evaluation Reporting","type":"guideline","priority":"P2","free":True,"url":"https://www.ispor.org/heor-resources/good-practices/article/cheers-2022"},
            {"id":"ISO-13606","title":"ISO 13606 Electronic Health Record Communication","type":"standard","priority":"P2","free":False,"purchase":"https://www.iso.org/standard/40784.html"},
            {"id":"ICH-E2B-R3","title":"ICH E2B(R3) Electronic Transmission of ICSRs","type":"standard","priority":"P2","free":True,"url":"https://www.ich.org/page/e2br3"},
            {"id":"ICH-E6-R3","title":"ICH E6(R3) Good Clinical Practice Guideline","type":"guideline","priority":"P1","free":True,"url":"https://database.ich.org/sites/default/files/ICH_E6_R3_Step4_DraftGuideline_2023_0504.pdf"},
        ]
    },
}

for k, v in NEW.items():
    d["categories"][k] = v

d["generated"] = datetime.now().isoformat()
IDX.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Added {len(NEW)} categories. Total: {len(d['categories'])}")
total = sum(len(c["standards"]) for c in d["categories"].values())
print(f"Total standards: {total}")
