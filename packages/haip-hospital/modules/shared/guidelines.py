"""Shared guideline reference loader — scans xhaip hospital knowledge guidelines.

Ported from haip-0710 (agents.domains.haip.rules.core.guidelines).
Adapted: guideline assets now live in packages/haip-hospital/knowledge/guidelines/.
"""

from __future__ import annotations

from pathlib import Path

_KNOWLEDGE_BASE = Path(__file__).resolve().parent.parent.parent / "knowledge" / "guidelines"


def _scan_dir(dir_path: Path, prefix: str = "") -> list[dict[str, str]]:
    """Recursively scan directory for guideline files."""
    if not dir_path.is_dir():
        return []
    results: list[dict[str, str]] = []
    for child in sorted(dir_path.iterdir()):
        rel = f"{prefix}/{child.name}" if prefix else child.name
        if child.is_file() and child.suffix.lower() in (".pdf", ".docx", ".txt", ".md", ".yaml", ".yml"):
            results.append({
                "name": child.stem,
                "type": "file",
                "path": rel,
            })
        elif child.is_dir():
            results.extend(_scan_dir(child, prefix=rel))
    return results


def available_guidelines() -> list[dict[str, str]]:
    """Return a list of available guideline files with name and path."""
    return _scan_dir(_KNOWLEDGE_BASE)


def guideline_base_path() -> Path:
    return _KNOWLEDGE_BASE
