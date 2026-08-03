"""Fix agents missing default roles using YAML in-place editing."""
import pathlib

import yaml

root = pathlib.Path(__file__).resolve().parent.parent / "packages" / "haip-hospital" / "agents" / "definitions"
fixed = []

for yf in sorted(root.glob("*.yaml")):
    content = yf.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    if not data or data.get("type") == "master_data":
        continue
    roles = data.get("ui", {}).get("roles", [])
    if not roles:
        continue
    has_default = any(r.get("default") for r in roles)
    if has_default:
        continue

    agent = data["name"]
    print(f"Fixing: {agent} (roles: {[r.get('id') for r in roles]})")

    first_role_id = roles[0].get("id", "")
    lines = content.splitlines(keepends=True)
    new_lines = []
    found_first_role_id = False
    label_found = False

    for line in lines:
        new_lines.append(line)
        if not found_first_role_id and f"- id: {first_role_id}" in line:
            found_first_role_id = True
            continue
        if found_first_role_id and not label_found:
            if "label:" in line:
                label_found = True
            continue
        if found_first_role_id and label_found:
            indent = " " * 4
            new_lines.append(f"{indent}default: true\n")
            found_first_role_id = False
            label_found = False

    fixed.append(agent)
    yf.write_text("".join(new_lines), encoding="utf-8")

print(f"\nFixed {len(fixed)} agents with no default role")
