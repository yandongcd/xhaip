"""Unified YAML asset loader — resolves xhaip hospital knowledge assets.

Ported from haip-0710 (agents.domains.haip.orthopedic_surgery.core.assets_loader).
Adapted: assets now live in packages/haip-hospital/knowledge/rules|guidelines/.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_KNOWLEDGE_BASE = Path(__file__).resolve().parent.parent.parent / "knowledge"
_RULES_DIR = _KNOWLEDGE_BASE / "rules"
_GUIDELINES_DIR = _KNOWLEDGE_BASE / "guidelines"

_ASSET_CACHE: dict[str, Any] = {}


def _find_asset(rel_path: str) -> Path | None:
    """Locate an asset YAML file under the knowledge directory."""
    candidate = _KNOWLEDGE_BASE / rel_path
    if candidate.exists():
        return candidate
    return None


def load_asset(rel_path: str, cache_key: str | None = None) -> dict[str, Any]:
    """Load a YAML asset file with caching.

    Args:
        rel_path: relative path under knowledge/, e.g. 'rules/completeness_rules.yaml'
        cache_key: optional explicit cache key (defaults to rel_path)

    Returns:
        dict with YAML contents, or {} if file not found
    """
    key = cache_key or rel_path
    if key in _ASSET_CACHE:
        return _ASSET_CACHE[key]

    path = _find_asset(rel_path)
    if path is None:
        _ASSET_CACHE[key] = {}
        return _ASSET_CACHE[key]

    import yaml
    with open(str(path), encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _ASSET_CACHE[key] = data if isinstance(data, dict) else {}
    return _ASSET_CACHE[key]


def reload_asset(rel_path: str) -> dict[str, Any]:
    """Force-reload an asset (clear cache)."""
    _ASSET_CACHE.pop(rel_path, None)
    _ASSET_CACHE.pop(rel_path.replace("/", "-"), None)
    return load_asset(rel_path)


def reload_all() -> None:
    """Clear entire asset cache."""
    _ASSET_CACHE.clear()


# ─── Convenience loaders ───

def load_guideline(guideline_id: str) -> dict[str, Any]:
    """Load a specific guideline ABB by its file name (without .yaml)."""
    return load_asset(f"guidelines/{guideline_id}.yaml", f"guideline-{guideline_id}")


def load_guideline_abbr(abbr: str) -> dict[str, Any] | None:
    """Find a guideline by its 'abbr' field."""
    if not _GUIDELINES_DIR.is_dir():
        return None
    for fname in sorted(os.listdir(str(_GUIDELINES_DIR))):
        if not fname.endswith(".yaml"):
            continue
        g = load_asset(f"guidelines/{fname}", f"guideline-{fname}")
        if g.get("abbr") == abbr:
            return g
    return None


def load_completeness_rules() -> dict[str, Any]:
    return load_asset("rules/completeness_rules.yaml", "completeness")


def load_complication_rules() -> dict[str, Any]:
    return load_asset("rules/complication_rules.yaml", "complication")


def load_nursing_rules() -> dict[str, Any]:
    return load_asset("rules/nursing_rules.yaml", "nursing")


def load_surgery_type_rules() -> dict[str, Any]:
    return load_asset("rules/surgery_type_rules.yaml", "surgery_type")


def load_followup_rules() -> dict[str, Any]:
    return load_asset("rules/followup_rules.yaml", "followup")


def load_timing_rules() -> dict[str, Any]:
    return load_asset("rules/timing_rules.yaml", "timing")


def load_rule_registry() -> dict[str, Any]:
    return load_asset("rules/registry.yaml", "rule_registry")
