"""修复辩论竞争对手双向对称性。

读入全部 YAML，为 anesthesia-risk / cardio-risk / pain-management / pharmacy
这三个核心基础 Agent 补全双向竞争对手，使其与所有引用方对称。
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

DEFS_DIR = Path(__file__).resolve().parent.parent / "packages" / "haip-hospital" / "agents" / "definitions"


def main(dry_run: bool = False):
    yaml_files = sorted(DEFS_DIR.glob("*.yaml"))
    agents: dict[str, dict] = {}
    file_map: dict[str, Path] = {}

    for yf in yaml_files:
        try:
            data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
            name = data.get("name", yf.stem)
            agents[name] = data
            file_map[name] = yf
        except Exception as e:
            print(f"SKIP: {yf.name} — {e}")

    # 收集所有引用 anesthesia-risk / cardio-risk / pain-management 的 Agent
    shared_agents = ["anesthesia-risk", "cardio-risk", "pain-management", "pharmacy"]
    incoming: dict[str, set[str]] = {sa: set() for sa in shared_agents}

    for name, data in agents.items():
        debate = data.get("debate", {})
        if debate.get("enabled"):
            competitors = debate.get("competitors", [])
            for c in competitors:
                if c in incoming:
                    incoming[c].add(name)

    # 修复共享 Agent 的 competitors
    changed = 0
    for sa in shared_agents:
        current = set(agents[sa].get("debate", {}).get("competitors", []))
        expected = incoming[sa]
        missing = expected - current
        if missing:
            data = agents[sa]
            if "debate" not in data:
                data["debate"] = {"enabled": True, "competitors": [], "mode": "auto"}
            data["debate"]["competitors"] = sorted(current | expected)
            agents[sa] = data
            if not dry_run:
                file_map[sa].write_text(
                    yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
                    encoding="utf-8",
                )
            print(f"  {sa}: +{sorted(missing)} (total: {len(current | expected)})")
            changed += 1

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Fixed: {changed} agents")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
