"""Anonymize patient names in patients.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

with open(ROOT / "packages" / "haip-hospital" / "data" / "patients.json", encoding="utf-8") as f:
    data = json.load(f)

for p in data["patients"]:
    name = p["name"]
    if len(name) <= 1:
        p["name"] = name + "*"
    elif len(name) == 2:
        p["name"] = name[0] + "*"
    else:
        p["name"] = name[0] + "*" * (len(name) - 1)

with open(ROOT / "packages" / "haip-hospital" / "data" / "patients.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

for p in data["patients"][:5]:
    print(f'{p["patient_id"]}: {p["name"]}')
print(f"Total: {len(data['patients'])} anonymized")
