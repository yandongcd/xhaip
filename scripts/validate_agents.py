"""Validate all agent YAML definitions against the JSON Schema."""
import json
import sys
from pathlib import Path

import yaml

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema not installed. Run: pip install jsonschema")
    sys.exit(1)

AGENT_DIR = Path(__file__).resolve().parent / "definitions"
SCHEMA_PATH = Path(__file__).resolve().parent / "agent-schema.json"


def main():
    if not SCHEMA_PATH.exists():
        print(f"ERROR: Schema not found: {SCHEMA_PATH}")
        sys.exit(1)

    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)

    yaml_files = sorted(AGENT_DIR.glob("*.yaml"))
    if not yaml_files:
        print("ERROR: No YAML agent definitions found")
        sys.exit(1)

    errors = 0
    for yf in yaml_files:
        try:
            with open(yf, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                print(f"ERROR: {yf.name} — empty or invalid YAML")
                errors += 1
                continue

            jsonschema.validate(instance=data, schema=schema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER)

            tool_count = len(data.get("tools", []))
            print(f"  OK  {yf.name} ({tool_count} tools)")

        except yaml.YAMLError as e:
            print(f"FAIL  {yf.name} — YAML parse error: {e}")
            errors += 1
        except jsonschema.ValidationError as e:
            print(f"FAIL  {yf.name} — {e.message}")
            print(f"       at: {'/'.join(str(p) for p in e.absolute_path)}")
            errors += 1
        except Exception as e:
            print(f"FAIL  {yf.name} — {e}")
            errors += 1

    total = len(yaml_files)
    passed = total - errors
    print(f"\n{'='*50}")
    print(f"Result: {passed}/{total} passed")

    if errors:
        print(f"ERROR: {errors} agent definition(s) failed validation")
        sys.exit(1)
    else:
        print("All agent definitions valid.")


if __name__ == "__main__":
    main()
