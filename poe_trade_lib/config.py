# poe_trade_lib/config.py
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class _Config:
    """A singleton class to load and provide access to the project's config.yaml."""

    def __init__(self) -> None:
        self._config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Loads configuration from config.yaml in the project root."""
        config_path = Path(__file__).parent.parent / "config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found at '{config_path}'. "
                "Ensure config.yaml is in the project root directory."
            )
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}") from e
        except OSError as e:
            raise FileNotFoundError(f"Could not read configuration file: {e}") from e

        if not isinstance(config, dict):
            raise ValueError("Configuration file must contain a YAML mapping")
        return config

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Retrieves a config value using a dot-separated path.
        Example: settings.get('api.base_url')
        """
        keys = key_path.split(".")
        value = self._config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            if default is not None:
                return default
            raise KeyError(
                f"Configuration key '{key_path}' not found and no default was provided."
            ) from None


settings = _Config()
