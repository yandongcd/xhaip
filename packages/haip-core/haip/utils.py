# haip/utils.py — shared utility functions for the HAIP project.
"""Shared project utilities."""

from __future__ import annotations

from pathlib import Path


def get_project_root() -> Path:
    """Return the xhaip project root directory (parent of packages/)."""
    return Path(__file__).resolve().parent.parent.parent.parent
