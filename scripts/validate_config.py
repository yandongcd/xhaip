"""配置一致性校验器 — 横切适配 X4。

检查全部 Agent YAML 的 debate / rag / learning 配置完整性。
覆盖之前遗漏的"覆盖度审计"步骤，确保所有 Agent 配置正确。

集成: CI 阻断 (python scripts/validate_config.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

DEFS_DIR = Path(__file__).resolve().parent.parent / "packages" / "haip-hospital" / "agents" / "definitions"
EXIT_ERROR = 1


def main():
    yaml_files = sorted(DEFS_DIR.glob("*.yaml"))
    agents: dict[str, dict] = {}
    errors = []
    warnings = []

    # ── 加载全部 YAML ──
    for yf in yaml_files:
        try:
            data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
            name = data.get("name", yf.stem)
            agents[name] = data
        except Exception as e:
            errors.append(f"PARSE: {yf.name} — {e}")

    agent_names = set(agents.keys())
    print(f"[1] Loaded {len(agents)} agents")

    # ── R1: debate.competitors 双向对称 + 目标 Agent 存在 + debate.enabled ──
    print("\n[R1] Debate competitor cross-validation")
    for name, data in agents.items():
        debate = data.get("debate", {})
        if not debate.get("enabled"):
            continue
        competitors = debate.get("competitors", [])
        for target in competitors:
            if target not in agent_names:
                errors.append(f"R1: [{name}] debate.competitors 引用不存在的 Agent: '{target}'")
            elif target == name:
                errors.append(f"R1: [{name}] debate.competitors 引用了自身")
            elif target in agents:
                target_debate = agents[target].get("debate", {})
                if not target_debate.get("enabled"):
                    warnings.append(f"R1: [{name}] -> [{target}] 但 [{target}] 的 debate.enabled=false")
                else:
                    target_competitors = target_debate.get("competitors", [])
                    if name not in target_competitors:
                        warnings.append(f"R1: [{name}] -> [{target}] 非双向: [{target}] 的 competitors 不含 [{name}]")

    # ── R2: rag 与 debate 一致性 ──
    print("\n[R2] RAG + Debate consistency")
    for name, data in agents.items():
        rag = data.get("rag", {})
        debate = data.get("debate", {})
        if debate.get("enabled") and not rag.get("enabled", True):
            warnings.append(f"R2: [{name}] debate=enabled 但 rag 未启用 — 声明提取质量可能下降")

    # ── R3: learning.auto_apply 含 A/B 实验配置 ──
    print("\n[R3] Learning A/B experiment config")
    for name, data in agents.items():
        learning = data.get("learning", {})
        auto = learning.get("auto_apply", [])
        if "prompt_opt" in auto and not learning.get("prompt_a_b", False):
            warnings.append(f"R3: [{name}] auto_apply 含 prompt_opt 但 prompt_a_b=false")

    # ── R4: depends_on 目标存在 ──
    print("\n[R4] depends_on reference validity")
    for name, data in agents.items():
        deps = data.get("depends_on", [])
        dep_names = [d.get("agent", "") if isinstance(d, dict) else str(d) for d in deps]
        for dep in dep_names:
            if dep and dep not in agent_names:
                errors.append(f"R4: [{name}] depends_on 引用不存在的 Agent: '{dep}'")

    # ── R5: 覆盖度统计 ──
    print("\n[R5] Coverage audit")
    rag_enabled = sum(1 for d in agents.values() if d.get("rag", {}).get("enabled", True))
    learn_enabled = sum(1 for d in agents.values() if d.get("learning", {}).get("enabled", False))
    debate_enabled = sum(1 for d in agents.values() if d.get("debate", {}).get("enabled", False))
    total = len(agents)

    print(f"  RAG:      {rag_enabled}/{total} ({rag_enabled * 100 // total}%)")
    print(f"  Learning: {learn_enabled}/{total} ({learn_enabled * 100 // total}%)")
    print(f"  Debate:   {debate_enabled}/{total} ({debate_enabled * 100 // total}%)")

    if rag_enabled < total:
        warnings.append(f"R5: {total - rag_enabled} agents missing rag config")
    if learn_enabled < total:
        errors.append(f"R5: {total - learn_enabled} agents missing learning config — CRITICAL")

    # ── R6: 死链检测 — depends_on 中引用的 Agent 也必须存在 ──
    print("\n[R6] Dead link detection")
    for name, data in agents.items():
        deps = data.get("depends_on", [])
        for dep in deps:
            dep_name = dep.get("agent", dep) if isinstance(dep, dict) else dep
            if dep_name and dep_name not in agents:
                errors.append(f"R6: [{name}] depends_on dead link: '{dep_name}'")

    # ── 输出 ──
    print(f"\n{'=' * 60}")
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  {w}")
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
    print(f"\nResult: {len(errors)} errors, {len(warnings)} warnings")

    if errors:
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    main()
