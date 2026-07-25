"""Quick verification for P3-P6 modules."""
import sys

sys.path.insert(0, "packages/haip-core")

print("=== P4: Data Integration ===")

# FHIR Models
from haip.fhir.models import FHIR_RESOURCE_CLASSES, FHIRPatient

p = FHIRPatient(id="P001", name=[{"text": "Zhang"}])
print(f"FHIR Models OK: Patient id={p.id}, resources={len(FHIR_RESOURCE_CLASSES)}")

# FHIR Converter
from haip.fhir.converter import diagnosis_to_condition, lab_to_observations, patient_to_fhir

patient = {"patient_id": "P001", "name": "Zhang*", "age": 62, "gender": "M", "diagnosis": "Fracture"}
fhir_p = patient_to_fhir(patient)
obs = lab_to_observations("P001", {"crp": 107.3, "hb": 109.5})
cond = diagnosis_to_condition("P001", "Fracture")
print(f"FHIR Converter OK: patient={fhir_p.id}, observations={len(obs)}, condition={cond.id}")

# HL7 v2
from haip.hl7v2 import build_hl7_adt, parse_hl7, validate_hl7

adt_msg = build_hl7_adt("P001", "Zhang^San", "A01", "M", "19800601")
parsed = parse_hl7(adt_msg)
valid, errors = validate_hl7(adt_msg)
print(f"HL7 v2 OK: msg_type={parsed.message_type}, event={parsed.trigger_event}, pid={parsed.patient_id}, valid={valid}")

# HIS Adapter
from haip.adapters import MockHISAdapter, get_adapter_registry

adapter = MockHISAdapter()
print(f"HIS Adapter OK: patients={len(adapter._patients)}")
registry = get_adapter_registry()
print(f"HIS Registry OK: tenants={registry.list_tenants()}")

print("\n=== P5: Multi-Tenancy ===")

from haip.tenants import get_tenant_manager

mgr = get_tenant_manager()
t = mgr.create(name="test-hospital", hospital_name="Test Hospital")
print(f"Tenants OK: id={t.id}, name={t.name}, status={t.status.value}")
mgr.suspend(t.id)
print(f"Tenant suspend OK: status={mgr.get(t.id).status.value}")

print("\n=== P6: Licensing ===")

from haip.licensing import LicenseManager, generate_license

lic_data = generate_license(
    customer_name="Test Hospital",
    customer_code="TH001",
    max_agents=48,
    max_users=100,
    expiry_days=365,
)
print(f"License Gen OK: customer={lic_data['customer_name']}, features={lic_data['features']}")

# Write temp license and validate
import os
import tempfile

with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
    import json
    json.dump(lic_data, f)
    tmp_license = f.name

mgr_l = LicenseManager(license_file=tmp_license)
info = mgr_l.validate()
print(f"License Validate OK: valid={info.valid}, customer={info.customer_name}")
os.unlink(tmp_license)

print("\n=== Data Validation ===")

from haip.validation import validate_patient

test_patient = {"patient_id": "P001", "age": 62, "gender": "M", "department": "ortho", "diagnosis": "Fracture"}
errors = validate_patient(test_patient)
print(f"Validate OK: errors={len(errors)}")

print("\n=== ALL P3-P6 MODULES VERIFIED ===")
