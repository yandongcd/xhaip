"""Configuration center — unified config loading with env override.

Supports:
    - YAML config file
    - Environment variable interpolation (${VAR:default})
    - Environment-specific overrides (dev/staging/prod)
    - Runtime config reload
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

_ENV_INTERPOLATION = re.compile(r"\$\{(\w+)(?::([^}]*))?\}")


def _interpolate_env(value: str) -> str:
    """Replace ${VAR:default} with environment variable or default."""

    def _replacer(m: re.Match) -> str:
        var = m.group(1)
        default = m.group(2) if m.group(2) is not None else ""
        return os.environ.get(var, default)

    return _ENV_INTERPOLATION.sub(_replacer, value)


def _interpolate_dict(data: dict) -> dict:
    """Recursively interpolate environment variables in a dict."""
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = _interpolate_env(value)
        elif isinstance(value, dict):
            result[key] = _interpolate_dict(value)
        elif isinstance(value, list):
            result[key] = [
                _interpolate_env(v) if isinstance(v, str) else v for v in value
            ]
        else:
            result[key] = value
    return result


class Config:
    """Unified configuration manager."""

    def __init__(self, config_dir: str | Path | None = None):
        if config_dir is None:
            # Auto-detect config directory
            candidates = [
                Path(__file__).resolve().parent.parent.parent.parent / "config",
                Path("config"),
            ]
            config_dir = next((c for c in candidates if c.exists()), Path("config"))
        self._config_dir = Path(config_dir)
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self):
        """Load main config and environment override."""
        # Load base config
        haip_yaml = self._config_dir / "haip.yaml"
        if haip_yaml.exists():
            with open(haip_yaml, encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}

        # Load environment override
        env = os.environ.get("HAIP_ENV", "dev")
        env_override = self._config_dir / f"haip.{env}.yaml"
        if env_override.exists():
            with open(env_override, encoding="utf-8") as f:
                override = yaml.safe_load(f) or {}
            self._deep_merge(self._data, override)

        # Interpolate environment variables
        self._data = _interpolate_dict(self._data)

    @staticmethod
    def _deep_merge(base: dict, override: dict):
        """Recursively merge override into base."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by dot-separated key (e.g. 'server.port')."""
        parts = key.split(".")
        node = self._data
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def get_section(self, key: str) -> dict[str, Any]:
        """Get an entire config section as a dict."""
        result = self.get(key, {})
        return result if isinstance(result, dict) else {}

    def reload(self):
        """Reload configuration from files."""
        self._load()

    @property
    def data(self) -> dict[str, Any]:
        return dict(self._data)


# Global singleton
_config: Config | None = None


def get_config() -> Config:
    """Get the global config singleton."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config():
    """Reload the global config."""
    if _config is not None:
        _config.reload()
