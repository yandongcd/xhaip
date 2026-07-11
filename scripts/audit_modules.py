#!/usr/bin/env python3
"""Module Implementation Dashboard — 对所有 Agent 的模块实现度进行审计.

Usage:
    python scripts/audit_modules.py              # 控制台表格
    python scripts/audit_modules.py --json       # JSON 输出
    python scripts/audit_modules.py --csv out.csv  # CSV 导出

检测逻辑:
  - 读取所有 agent YAML 定义 → 提取 handler 引用
  - 检查对应 Python 模块是否存在 → 函数是否存在
  - 统计模块行数与函数数
  - 输出实现等级: FULL / PARTIAL / STUB
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFINITIONS_DIR = PROJECT_ROOT / "packages" / "haip-hospital" / "agents" / "definitions"
MODULES_DIR = PROJECT_ROOT / "packages" / "haip-hospital" / "modules"


def load_yaml(path: Path) -> dict:
    """Load YAML without hard dependency on pyyaml at top level."""
    try:
        import yaml
    except ImportError:
        try:
            from haip.core_yaml import safe_load  # type: ignore[import-untyped]
            return safe_load(path.read_text(encoding="utf-8"))
        except ImportError:
            print("ERROR: PyYAML not available. Install: pip install pyyaml", file=sys.stderr)
            sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def scan_agent_definitions() -> list[dict]:
    """Scan all agent YAMLs and extract tool→handler mappings."""
    agents = []
    for yaml_path in sorted(DEFINITIONS_DIR.glob("*.yaml")):
        data = load_yaml(yaml_path)
        tools = []
        for t in data.get("tools", []):
            tools.append({
                "name": t.get("name", ""),
                "handler": t.get("handler", ""),
                "description": t.get("description", ""),
            })
        agents.append({
            "name": data.get("name", data.get("cn_name", yaml_path.stem)),
            "cn_name": data.get("cn_name", ""),
            "type": data.get("type", "business"),
            "department": data.get("department", ""),
            "tools": tools,
            "yaml_file": str(yaml_path),
        })
    return agents


def check_handler(handler: str) -> dict:
    """Check if a handler path resolves to a real Python module + function.

    Handler format: "orthopedics.clinical.analyze_xray"
    → module: modules/orthopedics/clinical.py
    → function: analyze_xray

    Returns: {module_exists, func_exists, file_path, line_count, func_count, error}
    """
    if not handler or "." not in handler:
        return {"module_exists": False, "func_exists": False, "file_path": "",
                "line_count": 0, "func_count": 0, "error": "Invalid handler format"}

    parts = handler.rsplit(".", 1)
    if len(parts) != 2:
        return {"module_exists": False, "func_exists": False, "file_path": "",
                "line_count": 0, "func_count": 0, "error": f"Bad handler: {handler}"}

    module_path, func_name = parts

    # Convert dotted path to filesystem path
    fs_path = MODULES_DIR / module_path.replace(".", "/")
    py_file = fs_path.with_suffix(".py")
    init_file = fs_path / "__init__.py"

    # Check which file actually exists
    actual_file = None
    if py_file.exists():
        actual_file = py_file
    elif init_file.exists():
        actual_file = init_file
    else:
        return {"module_exists": False, "func_exists": False, "file_path": str(py_file),
                "line_count": 0, "func_count": 0, "error": f"File not found: {py_file}"}

    # Count lines
    try:
        content = actual_file.read_text(encoding="utf-8")
        line_count = len(content.splitlines())
    except Exception:
        line_count = 0

    # Check if function exists
    import re
    func_found = bool(re.search(
        rf"^def\s+{re.escape(func_name)}\s*\(",
        content,
        re.MULTILINE
    ))

    # Count function definitions
    func_count = len(re.findall(r"^def\s+\w+\s*\(", content, re.MULTILINE))

    return {
        "module_exists": True,
        "func_exists": func_found,
        "file_path": str(actual_file),
        "line_count": line_count,
        "func_count": func_count,
        "error": "" if func_found else f"Function '{func_name}' not found in {actual_file.name}",
    }


def determine_implementation_level(tools: list[dict], checks: list[dict]) -> str:
    """Determine implementation level: FULL / PARTIAL / STUB."""
    if not tools:
        return "STUB"

    total = len(tools)
    resolved = sum(1 for c in checks if c["module_exists"])
    functional = sum(1 for c in checks if c["func_exists"])

    if resolved == 0:
        return "STUB"
    if functional == total:
        return "FULL"
    return "PARTIAL"


def build_report(agents: list[dict]) -> list[dict]:
    """Build full audit report."""
    report = []
    for agent in agents:
        tools = agent["tools"]
        checks = [check_handler(t["handler"]) for t in tools]
        level = determine_implementation_level(tools, checks)

        total_lines = sum(c["line_count"] for c in checks)
        total_funcs = sum(c["func_count"] for c in checks)
        resolved = sum(1 for c in checks if c["module_exists"])
        functional = sum(1 for c in checks if c["func_exists"])

        failures = [
            {"tool": t["name"], "handler": t["handler"], "error": c["error"]}
            for t, c in zip(tools, checks) if not c["func_exists"]
        ]

        report.append({
            "agent": agent["name"],
            "cn_name": agent["cn_name"],
            "type": agent["type"],
            "department": agent["department"],
            "tools_total": len(tools),
            "tools_resolved": resolved,
            "tools_functional": functional,
            "level": level,
            "total_lines": total_lines,
            "total_funcs": total_funcs,
            "failures": failures,
        })

    return report


def print_table(report: list[dict]):
    """Print report as formatted table."""
    headers = ["Agent", "Type", "Dept", "Tools", "OK", "Level", "Lines", "Funcs"]
    widths = [28, 10, 10, 6, 4, 8, 6, 6]

    header_row = "".join(h.ljust(w) for h, w in zip(headers, widths))
    sep = "-" * len(header_row)

    print(header_row)
    print(sep)

    stats = {"FULL": 0, "PARTIAL": 0, "STUB": 0}
    for r in report:
        stats[r["level"]] = stats.get(r["level"], 0) + 1
        row = [
            r["agent"][:27],
            r["type"][:9],
            r["department"][:9],
            str(r["tools_total"]),
            str(r["tools_functional"]),
            r["level"],
            str(r["total_lines"]),
            str(r["total_funcs"]),
        ]
        print("".join(v.ljust(w) for v, w in zip(row, widths)))

        # Print failures
        for f in r["failures"]:
            print(f"    FAIL: {f['tool']} → {f['handler']}")
            if f["error"]:
                print(f"          {f['error']}")

    print(sep)
    print(f"Summary: {len(report)} agents | FULL={stats['FULL']} PARTIAL={stats['PARTIAL']} STUB={stats['STUB']}")


def main():
    parser = argparse.ArgumentParser(description="Module Implementation Dashboard")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--csv", metavar="FILE", help="Export CSV to file")
    parser.add_argument("--agent", metavar="NAME", help="Filter by agent name")
    args = parser.parse_args()

    agents = scan_agent_definitions()
    if args.agent:
        agents = [a for a in agents if args.agent in a["name"]]

    report = build_report(agents)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.csv:
        with open(args.csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["agent", "cn_name", "type", "department", "tools_total",
                             "tools_functional", "level", "total_lines", "total_funcs",
                             "failures"])
            for r in report:
                writer.writerow([
                    r["agent"], r["cn_name"], r["type"], r["department"],
                    r["tools_total"], r["tools_functional"], r["level"],
                    r["total_lines"], r["total_funcs"],
                    len(r["failures"]),
                ])
        print(f"CSV written to {args.csv}")
    else:
        print_table(report)


if __name__ == "__main__":
    main()
