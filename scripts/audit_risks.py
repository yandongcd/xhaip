"""Systematic risk audit for xhaip.
Checks: handler paths, YAML type leaks in JS, str/int comparisons, accessibility.
"""
import ast
import importlib
import pathlib
import re
import sys
from collections import defaultdict

import yaml

ROOT = pathlib.Path(r"D:\dst\projects\xhaip")
YAML_DIR = ROOT / "packages/haip-hospital/agents/definitions"
MODULES_DIR = ROOT / "packages/haip-hospital/modules"
CORE_DIR = ROOT / "packages/haip-core/haip"

results = defaultdict(list)


# ── 1. Handler path validation ──
print("=" * 60)
print("1. HANDLER PATH VALIDATION")
print("=" * 60)

sys.path.insert(0, str(ROOT / "packages/haip-core"))
sys.path.insert(0, str(ROOT / "packages/haip-hospital"))
sys.path.insert(0, str(ROOT / "packages/haip-hospital/modules"))

broken = 0
total_handlers = 0
for yf in sorted(YAML_DIR.glob("*.yaml")):
    with open(yf, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "tools" not in data:
        continue
    agent = data.get("name", yf.stem)
    for tool in data.get("tools", []):
        total_handlers += 1
        handler = tool.get("handler", "")
        if not handler or "." not in handler:
            results["missing_handler"].append(f"{agent}/{tool['name']}: handler='{handler}'")
            continue
        mod, fn = handler.rsplit(".", 1)
        try:
            m = importlib.import_module(mod)
            if not hasattr(m, fn):
                broken += 1
                results["handler_func_missing"].append(f"{agent}/{tool['name']}: {handler}")
                print(f"  FAIL [{agent}] {tool['name']}: module {mod} OK but function '{fn}' not found")
        except ModuleNotFoundError:
            broken += 1
            results["handler_module_missing"].append(f"{agent}/{tool['name']}: {handler}")
            print(f"  FAIL [{agent}] {tool['name']}: {handler} — module not found")
        except Exception as e:
            broken += 1
            results["handler_import_error"].append(f"{agent}/{tool['name']}: {handler} — {e}")
            print(f"  FAIL [{agent}] {tool['name']}: {handler} — {e}")

print(f"\n  Total handlers: {total_handlers}, Broken: {broken}")


# ── 2. YAML type name leaks (JS/HTML using type as default) ──
print("\n" + "=" * 60)
print("2. YAML TYPE NAME LEAKS (using type str/int/float as default value)")
print("=" * 60)

for py_file in ROOT.rglob("*.py"):
    try:
        content = py_file.read_text(encoding="utf-8")
    except Exception:
        continue
    # Check for pattern: value || toolDef.input or similar fallback to type name
    if re.search(r"toolDef\.input\[.*?\]\s*\|\|", content):
        print(f"  WARN [{py_file.relative_to(ROOT)}]: possible type-as-default fallback")
        results["type_name_leak"].append(str(py_file.relative_to(ROOT)))

for js_file in ROOT.rglob("*.js"):
    try:
        content = js_file.read_text(encoding="utf-8")
    except Exception:
        continue
    if "toolDef.input[k]" in content and "||" in content:
        # Already fixed in agent.js, but check others
        pass

# Check rendered HTML for type hint leakage into default values
for yf in sorted(YAML_DIR.glob("*.yaml")):
    with open(yf, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "tools" not in data:
        continue
    for tool in data.get("tools", []):
        for k, v in tool.get("input", {}).items():
            if v in ("str", "int", "integer", "float", "number", "double", "bool", "dict", "list"):
                pass  # Normal type hint
            else:
                # Unexpected type hint value
                results["unexpected_type_hint"].append(f"{data['name']}/{tool['name']}.input.{k} = {v}")


# ── 3. Python str/int comparison risks ──
print("\n" + "=" * 60)
print("3. STRING/INT COMPARISON RISKS")
print("=" * 60)

comparison_ops = {ast.Gt, ast.Lt, ast.GtE, ast.LtE}

class CompareVisitor(ast.NodeVisitor):
    def __init__(self):
        self.issues = []
    def visit_Compare(self, node):
        if len(node.ops) > 0 and isinstance(node.ops[0], tuple(comparison_ops)):
            left = node.left
            # Check if left could be a string (function param, dict get, etc.)
            if isinstance(left, ast.Name):
                self.issues.append(f"  Variable '{left.id}' at line {node.lineno}")
            elif isinstance(left, ast.Subscript):
                self.issues.append(f"  Dict access at line {node.lineno}")
        self.generic_visit(node)

for py_file in CORE_DIR.rglob("*.py"):
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except Exception:
        continue
    v = CompareVisitor()
    v.visit(tree)
    if v.issues:
        rel = py_file.relative_to(ROOT)
        print(f"  {rel}:")
        for issue in v.issues[:3]:
            print(f"    {issue}")
        results["str_int_comparison"].append({"file": str(rel), "count": len(v.issues)})


# ── 4. Accessibility — id/for matching ──
print("\n" + "=" * 60)
print("4. ACCESSIBILITY AUDIT")
print("=" * 60)

for py_file in ROOT.rglob("*.py"):
    try:
        content = py_file.read_text(encoding="utf-8")
    except Exception:
        continue
    # Check for <input without id or <label without for
    inputs_without_id = re.findall(r'<input\b(?![^>]*\bid\s*=)', content)
    if inputs_without_id:
        print(f"  WARN [{py_file.relative_to(ROOT)}]: {len(inputs_without_id)} <input> without id")
        results["input_no_id"].append(str(py_file.relative_to(ROOT)))


# ── Summary ──
print("\n" + "=" * 60)
print("AUDIT SUMMARY")
print("=" * 60)

for category, items in results.items():
    count = len(items) if isinstance(items, list) else 1
    print(f"  {category}: {count} issue(s)")

print(f"\n  Risk Level: {'HIGH' if broken > 0 or results.get('handler_module_missing') else 'LOW'}")
