"""
YAML 知识库加载器 (knowledge_loader)

从 xhaip knowledge/ 目录加载围术期止吐相关的 YAML 知识文件
"""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "knowledge"
_ASSETS_CACHE: dict = {}


def _load_yaml(filename: str) -> dict:
    """加载 YAML 文件，带缓存"""
    if filename in _ASSETS_CACHE:
        return _ASSETS_CACHE[filename]

    paths = [
        _KNOWLEDGE_BASE_DIR / "guidelines" / filename,
        _KNOWLEDGE_BASE_DIR / "rules" / filename,
        _KNOWLEDGE_BASE_DIR / "guideline_sources" / filename,
        _KNOWLEDGE_BASE_DIR / "business_processes" / filename,
    ]

    for path in paths:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            _ASSETS_CACHE[filename] = data
            return data

    logger.warning("知识文件未找到: %s (路径: %s)", filename, path)
    return {}


def load_guideline_references() -> dict:
    """加载 2025 指南推荐意见"""
    return _load_yaml("anti_emetic_2025.yaml")


def load_regimens() -> dict:
    """加载用药方案矩阵"""
    return _load_yaml("anti_emetic_regimens.yaml")


def load_controls() -> dict:
    """加载管控规则库"""
    return _load_yaml("anti_emetic_controls.yaml")


def load_anesthesia_rules() -> dict:
    """加载麻醉管理规则"""
    return _load_yaml("anesthesia_ponv_rules.yaml")


def load_nondrug_rules() -> dict:
    """加载非药物干预规则"""
    return _load_yaml("non_drug_interventions.yaml")


def load_drug_db() -> dict:
    """加载止吐药数据库"""
    return _load_yaml("drug_db_antiemetic.yaml")


def search_knowledge(query: str = "", domain: str = "", **kwargs) -> dict:
    """关键词检索止吐知识库

    Args:
        query: 搜索关键词
        domain: 知识域 (guideline/regimen/controls/anesthesia/nondrug/drug/all)

    Returns:
        {results: [{source, content, guideline_refs}]}
    """
    if not query:
        return {"results": [], "status": "ok"}

    query_lower = query.lower()
    results = []
    domains_to_search = [domain] if domain and domain != "all" else [
        "guideline", "regimen", "controls", "anesthesia", "nondrug", "drug"
    ]

    search_map = {
        "guideline": ("anti_emetic_2025.yaml", "recommendations"),
        "regimen": ("anti_emetic_regimens.yaml", "regimens"),
        "controls": ("anti_emetic_controls.yaml", "rule_sets"),
        "anesthesia": ("anesthesia_ponv_rules.yaml", "rule_sets"),
        "nondrug": ("non_drug_interventions.yaml", "rule_sets"),
        "drug": ("drug_db_antiemetic.yaml", "drugs"),
    }

    for domain_name in domains_to_search:
        if domain_name not in search_map:
            continue
        filename, key = search_map[domain_name]
        data = _load_yaml(filename)
        items = data.get(key, []) if isinstance(data, dict) else []

        if not items:
            continue

        for item in items:
            item_str = str(item).lower()
            if query_lower in item_str:
                results.append({
                    "source": f"{domain_name}:{item.get('id', item.get('name', ''))}",
                    "name": item.get("name", item.get("statement", "")),
                    "guideline_refs": item.get("guideline_refs", item.get("guideline_ref", [])),
                })

    return {"results": results[:10], "total": len(results), "query": query, "status": "ok"}


def clear_cache() -> dict:
    """清除知识缓存"""
    _ASSETS_CACHE.clear()
    return {"status": "ok", "message": "知识缓存已清除"}
