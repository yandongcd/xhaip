"""批量扩容 Agent YAML 配置 — 为全部 58 Agent 添加 debate + learning + rag 配置段。

运行: python scripts/expand_agent_config.py
预览: python scripts/expand_agent_config.py --dry-run
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

DEFS_DIR = Path(__file__).resolve().parent.parent / "packages" / "haip-hospital" / "agents" / "definitions"

DEBATE_DEFAULT = {
    "enabled": True,
    "competitors": [],  # 自动从 depends_on 推导
    "mode": "auto",  # auto = Guard 冲突触发
}

LEARNING_DEFAULT = {
    "enabled": True,
    "auto_apply": ["citation_new", "route_adj"],
    "prompt_a_b": True,  # 允许 A/B 提示词实验
}

RAG_DEFAULT = {
    "enabled": True,
    "top_k": 5,
}

AGENT_COMPETITORS = {
    "orthopedic-surgery": ["cardio-risk", "anesthesia-risk", "pain-management", "mdt"],
    "cardio-surgery": ["cardio-risk", "anesthesia-risk"],
    "cardio-risk": ["orthopedic-surgery", "anesthesia-risk", "mdt"],
    "anesthesia-risk": ["orthopedic-surgery", "cardio-risk", "mdt"],
    "mdt": ["orthopedic-surgery", "cardio-risk", "anesthesia-risk", "pain-management"],
    "general-surgery": ["cardio-risk", "anesthesia-risk"],
    "neurosurgery": ["cardio-risk", "anesthesia-risk"],
    "thoracic-surgery": ["cardio-risk", "anesthesia-risk", "respiratory"],
    "vascular-surgery": ["cardio-risk", "anesthesia-risk"],
    "hepatobiliary-surgery": ["cardio-risk", "anesthesia-risk", "gastroenterology"],
    "renal-transplant": ["cardio-risk", "anesthesia-risk", "nephrology"],
    "burns-plastic": ["anesthesia-risk", "dermatology"],
    "breast-center": ["oncology", "anesthesia-risk"],
    "cosmetic-surgery": ["anesthesia-risk"],
    "interventional-therapy": ["cardio-risk", "anesthesia-risk", "cardiology"],
    "emergency": ["cardio-risk", "anesthesia-risk", "icu"],
    "icu": ["cardio-risk", "anesthesia-risk", "emergency"],
    "obgyn": ["anesthesia-risk", "neonatology"],
    "pain-hub": ["acute-pain", "chronic-pain", "cancer-pain", "interventional-pain"],
    "pharmacy": ["orthopedic-surgery", "cardio-surgery", "general-surgery"],
}


def main(dry_run: bool = False):
    yaml_files = sorted(DEFS_DIR.glob("*.yaml"))
    updated = 0
    skipped = 0

    for yf in yaml_files:
        try:
            data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(f"  SKIP {yf.name}: parse error ({e})")
            skipped += 1
            continue

        agent_name = data.get("name", yf.stem)
        deps = data.get("depends_on", [])
        dep_names = [d.get("agent", "") for d in deps] if isinstance(deps, list) else []

        changed = False

        # RAG: 全部 Agent 启用
        if "rag" not in data:
            data["rag"] = dict(RAG_DEFAULT)
            changed = True

        # Learning: 全部 Agent 启用
        if "learning" not in data:
            learning = dict(LEARNING_DEFAULT)
            learning["auto_apply"] = list(LEARNING_DEFAULT["auto_apply"])
            data["learning"] = learning
            changed = True

        # Debate: 有跨Agent依赖 或 手术/MDT相关 才启用
        if "debate" not in data:
            competitors = AGENT_COMPETITORS.get(agent_name, [])
            if not competitors and dep_names:
                # 过滤掉基础设施依赖 (master_data/architecture)
                clinical_deps = [n for n in dep_names if n not in ("medical-record", "metrics", "medical-docs")]
                if clinical_deps:
                    competitors = clinical_deps
            if competitors:
                debate = dict(DEBATE_DEFAULT)
                debate["competitors"] = list(competitors)
                data["debate"] = debate
                changed = True

        if changed:
            if not dry_run:
                yf.write_text(
                    yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
                    encoding="utf-8",
                )
            print(f"  UPDATE {agent_name}: rag+learning{'+debate' if 'debate' in data else ''}")
            updated += 1
        else:
            skipped += 1

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Updated: {updated}, Skipped: {skipped}, Total: {len(yaml_files)}")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
