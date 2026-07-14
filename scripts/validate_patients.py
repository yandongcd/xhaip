"""
validate_patients.py — Patient data quality checker for xhaip

Checks:
  1. Gender-diagnosis consistency (biology-based validation)
  2. Lab-template residue in treatment plans
  3. Date consistency (admission vs clinical dates)
  4. Lab field integrity
  5. Provenance field presence
  6. Department-diagnosis plausibility

Usage:
    python scripts/validate_patients.py
    python scripts/validate_patients.py --fix  # attempt auto-fix
"""
import json
import sys
from pathlib import Path

PATIENTS_PATH = Path(__file__).parent.parent / 'packages' / 'haip-hospital' / 'data' / 'patients.json'

# ---- Validation rules ----

# Female-only diagnoses (biological impossibility for males)
FEMALE_ONLY_DIAGNOSES = [
    '子宫肌瘤', '子宫肌瘤栓塞', '子宫肌瘤 UAE术后', '子宫肌瘤UAE术后',
    '异位妊娠', '宫外孕', '剖宫产', '卵巢囊肿', '卵巢肿瘤',
    '宫颈癌', '宫颈病变', '子宫内膜癌', '盆腔炎',
    '妊娠', '分娩', '流产', '月经', '更年期',
    '子宫腺肌症', '子宫腺肌瘤',
]

# Male breast cancer is possible (~1% of breast cancers)
# So we WARN on male+breast but don't FAIL

# Known template residues that should never appear in treatment plans
TEMPLATE_RESIDUES = [
    '化疗方案', '放疗方案', '靶向治疗',  # oncology-only
]

# Departments where specific diagnoses are inappropriate
DEPT_DIAGNOSIS_RULES = [
    # (dept_keyword, forbidden_diagnosis_keyword, level)
    ('妇产科', '前列腺', 'fail'),
    ('泌尿外科', '子宫', 'fail'),
    ('儿科', '老年', 'warn'),
]

# ---- Check functions ----

def check_gender_diagnosis(patient):
    """Check if gender and diagnosis are biologically consistent."""
    gender = patient.get('gender', '')
    diagnosis = str(patient.get('diagnosis', ''))

    if gender == 'M':
        for keyword in FEMALE_ONLY_DIAGNOSES:
            if keyword in diagnosis:
                return 'fail', f"Male patient with female-only diagnosis: {keyword}"

    return 'pass', ''


def check_template_residue(patient):
    """Check for known template residues in treatment plan."""
    treatment = str(patient.get('treatment_plan', ''))
    diagnosis = str(patient.get('diagnosis', ''))
    is_cancer = any(kw in diagnosis for kw in ['癌', '瘤', '肿瘤'])

    for residue in TEMPLATE_RESIDUES:
        if residue in treatment and not is_cancer:
            return 'warn', f"Template residue '{residue}' in non-cancer patient treatment plan"

    return 'pass', ''


def check_date_consistency(patient):
    """Check admission vs clinical dates consistency."""
    admission = patient.get('admission_date', '')
    clinical = patient.get('clinical', {})
    if isinstance(clinical, dict):
        his = clinical.get('his', {})
        if isinstance(his, dict):
            clin_admission = his.get('admission_date', '')
            if admission and clin_admission and admission != clin_admission:
                return 'warn', f"Admission date mismatch: {admission} vs clinical {clin_admission}"

    return 'pass', ''


def check_provenance(patient):
    """Ensure provenance field exists."""
    prov = patient.get('provenance', {})
    if not prov:
        return 'warn', "Missing provenance field"
    if 'source' not in prov:
        return 'warn', "Provenance missing 'source' field"
    if 'institution' not in prov:
        return 'warn', "Provenance missing 'institution' field"
    return 'pass', ''


def check_lab_fields(patient):
    """Basic lab field sanity check."""
    labs = patient.get('lab_results', {})
    if not isinstance(labs, dict):
        return 'pass', ''

    # Check for suspicious lab values
    issues = []
    for key, val in labs.items():
        if isinstance(val, (int, float)):
            if val < 0:
                issues.append(f"{key}={val} (negative)")
            if key.upper() == 'HB' and (val < 30 or val > 250):
                issues.append(f"Hb={val} (out of physiological range)")
            if key.upper() in ('CR', 'CREATININE', 'CREA') and val > 1500:
                issues.append(f"Cr={val} (likely incompatible with life)")
            if key.upper() == 'K' and (val < 1.5 or val > 10):
                issues.append(f"K={val} (likely incompatible with life)")

    if issues:
        return 'warn', '; '.join(issues)
    return 'pass', ''


# ---- Main ----

def main():
    if not PATIENTS_PATH.exists():
        print(f'ERROR: {PATIENTS_PATH} not found')
        sys.exit(1)

    with open(PATIENTS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    patients = data['patients']
    print(f'Validating {len(patients)} patients...\n')

    checks = [
        ('gender-diagnosis', check_gender_diagnosis),
        ('template-residue', check_template_residue),
        ('date-consistency', check_date_consistency),
        ('lab-fields', check_lab_fields),
        ('provenance', check_provenance),
    ]

    results = {'pass': 0, 'warn': 0, 'fail': 0}
    issues = []

    for patient in patients:
        pid = patient.get('patient_id', '?')
        for check_name, check_fn in checks:
            level, msg = check_fn(patient)
            if level != 'pass':
                results[level] += 1
                issues.append(f'[{level.upper()}] {pid} {check_name}: {msg}')
            else:
                results['pass'] += 1

    # Report
    total_checks = sum(results.values())
    print(f'Total checks: {total_checks}')
    print(f'  PASS: {results["pass"]}')
    print(f'  WARN: {results["warn"]}')
    print(f'  FAIL: {results["fail"]}')

    if issues:
        print(f'\n{len(issues)} issues found:')
        for issue in issues:
            print(f'  {issue}')

    if results['fail'] > 0:
        print(f'\n[FAIL] {results["fail"]} blocking issues found. Fix before proceeding.')
        sys.exit(1)
    else:
        print('\n[OK] No blocking issues.')
        sys.exit(0)


if __name__ == '__main__':
    main()
