"""User configuration management for Model Manager."""

import json
import logging
from pathlib import Path
from typing import Any

from src.exceptions import StorageError

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "model-manager"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_MODELS_DIR = Path.home() / "models"
DEFAULT_CACHE_DURATION = 300  # 5 minutes
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 1
DEFAULT_DOWNLOAD_TIMEOUT = 300  # 5 minutes


class ConfigManager:
    """
    Manages user configuration for Model Manager.

    Handles loading, saving, and accessing configuration values
    from a YAML configuration file.
    """

    def __init__(self, config_file: Path | None = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to configuration file. If None, uses default location.
        """
        self.config_file = config_file or DEFAULT_CONFIG_FILE
        self._config: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file, or create defaults."""
        # Create config directory if it doesn't exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config if it exists
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self._config = json.load(f)
                logger.info(f"Loaded configuration from {self.config_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(
                    f"Failed to load config from {self.config_file}: {e}. Using defaults."
                )
                self._config = {}
        else:
            logger.info("No configuration file found, using defaults")
            self._config = {}
            # Create empty config file for user to edit
            self._save_config()

    def _save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self._config, f, indent=2)
            logger.info(f"Saved configuration to {self.config_file}")
        except IOError as e:
            raise StorageError(f"Failed to save configuration: {e}") from e

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key (supports nested keys with dot notation,
                e.g., "download.timeout")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        # Handle nested keys with dot notation
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key (supports nested keys with dot notation)
            value: Value to set
        """
        # Handle nested keys with dot notation
        keys = key.split(".")
        config = self._config

        # Navigate to parent of final key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set final key
        config[keys[-1]] = value

        self._save_config()

    def get_models_dir(self) -> Path:
        """
        Get models directory path.

        Returns:
            Path to models directory
        """
        path_str = self.get("models_dir", str(DEFAULT_MODELS_DIR))
        path = Path(path_str)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_cache_duration(self) -> int:
        """
        Get cache duration in seconds.

        Returns:
            Cache duration in seconds
        """
        return self.get("cache.duration", DEFAULT_CACHE_DURATION)

    def get_max_concurrent_downloads(self) -> int:
        """
        Get maximum concurrent downloads.

        Returns:
            Maximum number of concurrent downloads
        """
        return self.get("download.max_concurrent", DEFAULT_MAX_CONCURRENT_DOWNLOADS)

    def get_download_timeout(self) -> int:
        """
        Get download timeout in seconds.

        Returns:
            Download timeout in seconds
        """
        return self.get("download.timeout", DEFAULT_DOWNLOAD_TIMEOUT)

    def set_models_dir(self, path: Path | str) -> None:
        """
        Set models directory path.

        Args:
            path: Path to models directory
        """
        if isinstance(path, str):
            path = Path(path)
        self.set("models_dir", str(path))

    def set_cache_duration(self, seconds: int) -> None:
        """
        Set cache duration in seconds.

        Args:
            seconds: Cache duration in seconds
        """
        self.set("cache.duration", seconds)

    def set_max_concurrent_downloads(self, count: int) -> None:
        """
        Set maximum concurrent downloads.

        Args:
            count: Maximum number of concurrent downloads
        """
        self.set("download.max_concurrent", count)

    def set_download_timeout(self, seconds: int) -> None:
        """
        Set download timeout in seconds.

        Args:
            seconds: Download timeout in seconds
        """
        self.set("download.timeout", seconds)

    def reset_to_defaults(self) -> None:
        """Reset all configuration to default values."""
        self._config = {}
        self._save_config()
        logger.info("Configuration reset to defaults")
