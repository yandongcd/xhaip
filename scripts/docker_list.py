"""Generate docker-compose from agent YAML definitions."""
import yaml
import os
from pathlib import Path

DEFS_DIR = Path("packages/haip-hospital/agents/definitions")
PROFILES = {
    "core": {"medical-record", "metrics", "pharmacy", "portal"},
    "surgical": {"orthopedic-surgery", "cardio-surgery", "cardio-risk", "anesthesia-risk",
                  "neurosurgery", "general-surgery", "hepatobiliary-surgery", 
                  "vascular-surgery", "thoracic-surgery", "breast-center",
                  "burns-plastic", "cosmetic-surgery", "renal-transplant",
                  "interventional-therapy"},
    "medical": {"cardiology", "respiratory", "gastroenterology", "nephrology",
                "endocrinology", "hematology", "rheumatology", "infectious-disease",
                "oncology", "geriatrics"},
    "emergency": {"emergency", "icu"},
    "women-children": {"obgyn", "pediatrics", "neonatology"},
    "specialty": {"ophthalmology", "ent", "stomatology", "dermatology",
                  "psychiatry", "rehabilitation", "tcm", "health-management",
                  "huigiao"},
    "pain": {"pain-hub"},
    "arch": {"togaf"},
}
DEPENDS = {
    "orthopedic-surgery": ["medical-record", "cardio-risk", "anesthesia-risk"],
    "cardio-surgery": ["medical-record", "cardio-risk"],
    "neurosurgery": ["medical-record"],
    "general-surgery": ["medical-record"],
}

agents = []
for f in sorted(DEFS_DIR.glob("*.yaml")):
    with open(f, encoding="utf-8") as fh:
        d = yaml.safe_load(fh)
    port = d.get("port", 0)
    if port > 0:
        agents.append((d["name"], d["cn_name"], port))

# Count
print(f"Agents with ports: {len(agents)}")
print(f"Profiles: {list(PROFILES.keys())}")

# Print per-profile agent list
for profile, names in PROFILES.items():
    count = sum(1 for n, _, _ in agents if n in names)
    print(f"  {profile}: {count} agents")

# Print agent -> port mapping
print("\nPort allocations:")
for name, cn, port in sorted(agents, key=lambda x: x[2]):
    profiles_for = [p for p, ns in PROFILES.items() if name in ns] or ["(none)"]
    deps = DEPENDS.get(name, [])
    dep_str = f" → depends: {deps}" if deps else ""
    print(f"  :{port:<6} {name:<28} {cn:<18} [{','.join(profiles_for)}]{dep_str}")
