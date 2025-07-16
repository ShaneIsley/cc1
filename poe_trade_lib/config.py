# poe_trade_lib/config.py
from pathlib import Path

import yaml


class _Config:
    """A singleton class to load and provide access to the project's config.yaml."""

    def __init__(self):
        self._config = self._load_config()

    def _load_config(self):
        """Loads configuration from config.yaml in the project root."""
        config_path = Path(__file__).parent.parent / "config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found at '{config_path}'. "
                "Ensure config.yaml is in the project root directory."
            )
        with open(config_path) as f:
            return yaml.safe_load(f)

    def get(self, key_path: str, default=None):
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
