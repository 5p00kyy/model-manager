"""Tests for configuration manager."""

import json
import pytest
import tempfile
import shutil
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.config_manager import ConfigManager, DEFAULT_MODELS_DIR
from src.exceptions import StorageError


class TestConfigManagerInitialization:
    """Test suite for ConfigManager initialization."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def config_file(self, temp_dir):
        """Create a temporary config file."""
        return temp_dir / "config.json"

    def test_initialization_creates_config_dir(self, config_file):
        """Test that initialization creates config directory."""
        manager = ConfigManager(config_file)
        assert config_file.parent.exists()
        assert config_file.exists()

    def test_initialization_with_existing_config(self, config_file, temp_dir):
        """Test initialization with existing config file."""
        # Create existing config
        config_data = {"models_dir": "/custom/path"}
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        manager = ConfigManager(config_file)
        assert manager.get("models_dir") == "/custom/path"

    def test_initialization_with_invalid_json(self, config_file):
        """Test initialization with invalid JSON uses defaults."""
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            f.write("invalid json")

        manager = ConfigManager(config_file)
        assert manager.get("models_dir") is None

    def test_initialization_without_file(self, temp_dir):
        """Test initialization without config file."""
        config_file = temp_dir / "nonexistent.json"
        manager = ConfigManager(config_file)
        assert manager.get("models_dir") is None


class TestConfigManagerGetSet:
    """Test suite for ConfigManager get/set operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def config_file(self, temp_dir):
        """Create a temporary config file."""
        return temp_dir / "config.json"

    @pytest.fixture
    def config_manager(self, config_file):
        """Create a ConfigManager instance."""
        return ConfigManager(config_file)

    def test_get_simple_key(self, config_manager):
        """Test getting a simple key."""
        config_manager.set("test_key", "test_value")
        assert config_manager.get("test_key") == "test_value"

    def test_get_with_default(self, config_manager):
        """Test getting key with default value."""
        assert config_manager.get("nonexistent", "default") == "default"

    def test_get_nonexistent_without_default(self, config_manager):
        """Test getting nonexistent key without default."""
        assert config_manager.get("nonexistent") is None

    def test_get_nested_key(self, config_manager):
        """Test getting nested keys with dot notation."""
        config_manager.set("section.key", "value")
        assert config_manager.get("section.key") == "value"

    def test_set_simple_key(self, config_manager, config_file):
        """Test setting a simple key."""
        config_manager.set("test_key", "test_value")

        # Verify it was saved
        with open(config_file, "r") as f:
            config = json.load(f)
        assert config["test_key"] == "test_value"

    def test_set_nested_key(self, config_manager, config_file):
        """Test setting nested keys with dot notation."""
        config_manager.set("section.subsection.key", "value")

        # Verify structure
        with open(config_file, "r") as f:
            config = json.load(f)
        assert config["section"]["subsection"]["key"] == "value"

    def test_set_overwrites_existing(self, config_manager, config_file):
        """Test that set overwrites existing value."""
        config_manager.set("key", "value1")
        config_manager.set("key", "value2")

        assert config_manager.get("key") == "value2"

    def test_set_different_types(self, config_manager):
        """Test setting values of different types."""
        config_manager.set("string", "text")
        config_manager.set("int", 123)
        config_manager.set("float", 1.5)
        config_manager.set("bool", True)
        config_manager.set("list", [1, 2, 3])
        config_manager.set("dict", {"nested": "value"})

        assert config_manager.get("string") == "text"
        assert config_manager.get("int") == 123
        assert config_manager.get("float") == 1.5
        assert config_manager.get("bool") is True
        assert config_manager.get("list") == [1, 2, 3]
        assert config_manager.get("dict") == {"nested": "value"}


class TestConfigManagerConvenienceMethods:
    """Test suite for ConfigManager convenience methods."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def config_file(self, temp_dir):
        """Create a temporary config file."""
        return temp_dir / "config.json"

    @pytest.fixture
    def config_manager(self, config_file):
        """Create a ConfigManager instance."""
        return ConfigManager(config_file)

    def test_get_models_dir_default(self, config_manager):
        """Test getting default models directory."""
        models_dir = config_manager.get_models_dir()
        assert models_dir == DEFAULT_MODELS_DIR
        assert models_dir.exists()

    def test_set_models_dir(self, config_manager, temp_dir):
        """Test setting models directory."""
        custom_path = temp_dir / "custom_models"
        config_manager.set_models_dir(custom_path)

        assert config_manager.get_models_dir() == custom_path
        assert custom_path.exists()

    def test_get_cache_duration_default(self, config_manager):
        """Test getting default cache duration."""
        duration = config_manager.get_cache_duration()
        assert duration == 300

    def test_set_cache_duration(self, config_manager):
        """Test setting cache duration."""
        config_manager.set_cache_duration(600)
        assert config_manager.get_cache_duration() == 600

    def test_get_max_concurrent_downloads_default(self, config_manager):
        """Test getting default max concurrent downloads."""
        max_downloads = config_manager.get_max_concurrent_downloads()
        assert max_downloads == 1

    def test_set_max_concurrent_downloads(self, config_manager):
        """Test setting max concurrent downloads."""
        config_manager.set_max_concurrent_downloads(3)
        assert config_manager.get_max_concurrent_downloads() == 3

    def test_get_download_timeout_default(self, config_manager):
        """Test getting default download timeout."""
        timeout = config_manager.get_download_timeout()
        assert timeout == 300

    def test_set_download_timeout(self, config_manager):
        """Test setting download timeout."""
        config_manager.set_download_timeout(600)
        assert config_manager.get_download_timeout() == 600

    def test_reset_to_defaults(self, config_manager, config_file):
        """Test resetting configuration to defaults."""
        config_manager.set("custom_key", "custom_value")
        assert config_manager.get("custom_key") == "custom_value"

        config_manager.reset_to_defaults()

        assert config_manager.get("custom_key") is None

    def test_models_dir_with_string(self, config_manager, temp_dir):
        """Test setting models directory with string path."""
        custom_path = temp_dir / "custom_models"
        config_manager.set_models_dir(str(custom_path))

        assert config_manager.get_models_dir() == custom_path


class TestConfigManagerPersistence:
    """Test suite for ConfigManager persistence."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def config_file(self, temp_dir):
        """Create a temporary config file."""
        return temp_dir / "config.json"

    @pytest.fixture
    def config_manager(self, config_file):
        """Create a ConfigManager instance."""
        return ConfigManager(config_file)

    def test_config_persists_across_instances(self, config_file):
        """Test that config persists across ConfigManager instances."""
        manager1 = ConfigManager(config_file)
        manager1.set("test_key", "test_value")

        # Create new instance with same config file
        manager2 = ConfigManager(config_file)
        assert manager2.get("test_key") == "test_value"

    def test_config_survives_restart(self, config_file):
        """Test that config file survives simulated restart."""
        manager1 = ConfigManager(config_file)
        manager1.set("key1", "value1")
        manager1.set("key2", "value2")

        # Simulate restart by creating new instance
        manager2 = ConfigManager(config_file)
        assert manager2.get("key1") == "value1"
        assert manager2.get("key2") == "value2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
