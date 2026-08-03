# @origin: haip-0710/src/agents/domains/haip/orthopedic_surgery/core/completeness.py
# @origin_repo: https://github.com/yandongcd/haip
# @ported_date: 2026-07-12
# @status: ADAPTED (imports rewritten for xhaip engine)
#   Key deps to adapt:
#     agents.domains.haip.core.* -> packages/haip-hospital/modules/shared/
#     agents.harness.* -> packages/haip-core/haip/
#     Rule path resolution -> packages/haip-hospital/knowledge/rules/
"""F4.1 检查完整性校验 — 规则从 YAML 动态加载."""

from __future__ import annotations

from typing import Any

from shared.assets_loader import load_completeness_rules


# ASSET:rule-hip-fracture-completeness
def check_test_completeness(patient: dict[str, Any]) -> dict[str, Any]:
    """Check which required tests/exams the patient has completed.

    Rules loaded dynamically from assets/rules/completeness_rules.yaml.
    """
    rules = load_completeness_rules()
    required_tests: list[dict] = rules.get("required_tests", [])
    required_exams: list[dict] = rules.get("required_exams", [])

    lab_tests = patient.get("lab_tests", [])
    lab_names = {t.get("name", "") for t in lab_tests}
    lab_names_lower = {n.lower() for n in lab_names}

    examinations = patient.get("examinations", [])
    exam_names = {e.get("name", "") for e in examinations}
    exam_names_lower = {n.lower() for n in exam_names}

    combined_lower = lab_names_lower | exam_names_lower

    def _is_found(items: list[str]) -> bool:
        for item in items:
            il = item.lower()
            if any(il in cl or cl in il for cl in combined_lower):
                return True
        return False

    def _is_exam_found(keywords: list[str]) -> bool:
        for kw in keywords:
            kwl = kw.lower()
            if any(kwl in cl or cl in kwl for cl in combined_lower):
                return True
        return False

    test_results = []
    for req in required_tests:
        found = _is_found(req.get("items", []))
        test_results.append({
            "id": req["id"],
            "category": req.get("category", ""),
            "name": req.get("name", ""),
            "required_items": req.get("items", []),
            "found": found,
            "reason": req.get("reason", ""),
            "guideline": req.get("guideline_ref", ""),
            "phase": req.get("phase", ""),
            "dept": req.get("dept", ""),
            "agents": req.get("agents", []),
        })

    exam_results = []
    for req in required_exams:
        name = req.get("name", "")
        keywords = [name] + name.replace("/", " ").split()
        found = _is_exam_found(keywords)
        exam_results.append({
            "id": req["id"],
            "category": req.get("category", ""),
            "name": name,
            "found": found,
            "reason": req.get("reason", ""),
            "guideline": req.get("guideline_ref", ""),
            "phase": req.get("phase", ""),
            "dept": req.get("dept", ""),
            "agents": req.get("agents", []),
        })

    all_items = test_results + exam_results
    total = len(all_items)
    completed = sum(1 for i in all_items if i["found"])
    completeness_pct = round(completed / total * 100, 1) if total > 0 else 0.0

    missing_items = [i for i in all_items if not i["found"]]
    missing_by_phase: dict[str, list[str]] = {}
    for item in missing_items:
        phase = item.get("phase", "其他")
        if phase not in missing_by_phase:
            missing_by_phase[phase] = []
        missing_by_phase[phase].append(f"{item['category']}({item['name']})")

    recommendations = []
    for phase, items in missing_by_phase.items():
        recommendations.append(f"{phase}阶段缺少:{' '.join(items)}")

    return {
        "test_categories": test_results,
        "exam_categories": exam_results,
        "completeness_pct": completeness_pct,
        "total_required": total,
        "completed": completed,
        "missing_items": missing_items,
        "missing_by_phase": missing_by_phase,
        "recommendations": recommendations,
    }


def print_completeness_report(result: dict[str, Any]) -> None:
    """Pretty-print the completeness check result."""
    print("===== 检查完整性校验 =====")
    print(f"完成度: {result['completeness_pct']}% ({result['completed']}/{result['total_required']})")
    print()

    print("--- 检验项目 ---")
    for t in result["test_categories"]:
        status = "[OK]" if t["found"] else "[缺]"
        print(f"  {status} {t['category']} ({t['name']}) — {t['reason']}")

    print()
    print("--- 检查项目 ---")
    for e in result["exam_categories"]:
        status = "[OK]" if e["found"] else "[缺]"
        print(f"  {status} {e['category']} ({e['name']}) — {e['reason']}")

    if result["recommendations"]:
        print()
        print("缺失检查建议:")
        for rec in result["recommendations"]:
            print(f"  - {rec}")
    else:
        print()
        print("所有必要检查已完成 ")
