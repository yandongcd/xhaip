"""一次性脚本: 为 patients.json 中缺失 provenance 的记录补齐字段 (T1)。

与已有 provenance 记录保持一致格式:
  source: synthetic | origin_repo: xhaip_v1.0 | institution: xhaip_patient_generator
  deidentified: True | generation_date: 2026-07-10 | provenance_added: 2026-07-12
"""
from __future__ import annotations

import json
from pathlib import Path

PATIENTS_FILE = Path(__file__).resolve().parent.parent / "packages" / "haip-hospital" / "data" / "patients.json"

TEMPLATE = {
    "source": "synthetic",
    "origin_repo": "xhaip_v1.0",
    "institution": "xhaip_patient_generator",
    "deidentified": True,
    "generation_date": "2026-07-10",
    "provenance_added": "2026-07-12",
}


def main() -> int:
    data = json.loads(PATIENTS_FILE.read_text(encoding="utf-8"))
    patients = data.get("patients", data.get("data", []))
    if not isinstance(patients, list):
        raise SystemExit(f"Unexpected patients container: {type(patients)}")

    added = 0
    for pt in patients:
        if "provenance" not in pt:
            pt["provenance"] = dict(TEMPLATE)
            added += 1

    PATIENTS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"patched {added} records in {PATIENTS_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
