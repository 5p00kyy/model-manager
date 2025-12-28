"""Tests for storage manager."""

import json
import pytest
import shutil
import tempfile
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.storage import StorageManager
from src.exceptions import StorageError


class TestStorageManagerInitialization:
    """Test suite for StorageManager initialization."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    def test_initialization_creates_models_dir(self, temp_dir):
        """Test that initialization creates the models directory."""
        models_dir = temp_dir / "models"
        metadata_file = temp_dir / ".metadata.json"

        assert not models_dir.exists()

        storage = StorageManager(models_dir, metadata_file)

        assert models_dir.exists()
        assert storage.models_dir == models_dir
        assert storage.metadata_file == metadata_file

    def test_initialization_existing_dir(self, temp_dir):
        """Test initialization with existing directory."""
        models_dir = temp_dir / "models"
        models_dir.mkdir()
        metadata_file = temp_dir / ".metadata.json"

        storage = StorageManager(models_dir, metadata_file)

        assert storage.models_dir == models_dir

    def test_initialization_loads_existing_metadata(self, temp_dir):
        """Test that initialization loads existing metadata."""
        models_dir = temp_dir / "models"
        models_dir.mkdir()
        metadata_file = temp_dir / ".metadata.json"

        # Create existing metadata
        metadata = {"author/model": {"commit_sha": "abc123"}}
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        storage = StorageManager(models_dir, metadata_file)

        assert storage.metadata == metadata

    def test_initialization_empty_metadata(self, temp_dir):
        """Test initialization with no existing metadata."""
        models_dir = temp_dir / "models"
        metadata_file = temp_dir / ".metadata.json"

        storage = StorageManager(models_dir, metadata_file)

        assert storage.metadata == {}


class TestScanLocalModels:
    """Test suite for scan_local_models method."""

    @pytest.fixture
    def storage(self):
        """Create a StorageManager instance with temp directories."""
        tmpdir = tempfile.mkdtemp()
        models_dir = Path(tmpdir) / "models"
        metadata_file = Path(tmpdir) / ".metadata.json"
        storage = StorageManager(models_dir, metadata_file)
        yield storage
        shutil.rmtree(tmpdir)

    def test_scan_empty_directory(self, storage):
        """Test scanning empty models directory."""
        models = storage.scan_local_models()
        assert models == []

    def test_scan_with_models(self, storage):
        """Test scanning directory with models."""
        # Create model structure
        model_dir = storage.models_dir / "author" / "model-name"
        model_dir.mkdir(parents=True)

        # Create GGUF file
        gguf_file = model_dir / "model.gguf"
        gguf_file.write_bytes(b"fake gguf content" * 100)

        models = storage.scan_local_models()

        assert len(models) == 1
        assert models[0]["repo_id"] == "author/model-name"
        assert models[0]["files"] == ["model.gguf"]
        assert models[0]["total_size"] > 0

    def test_scan_multiple_models(self, storage):
        """Test scanning with multiple models."""
        # Create two models
        for author, name in [("author1", "model1"), ("author2", "model2")]:
            model_dir = storage.models_dir / author / name
            model_dir.mkdir(parents=True)
            (model_dir / "model.gguf").write_bytes(b"content")

        models = storage.scan_local_models()

        assert len(models) == 2
        repo_ids = [m["repo_id"] for m in models]
        assert "author1/model1" in repo_ids
        assert "author2/model2" in repo_ids

    def test_scan_ignores_non_gguf(self, storage):
        """Test that scan ignores directories without GGUF files."""
        model_dir = storage.models_dir / "author" / "model"
        model_dir.mkdir(parents=True)

        # Only non-GGUF files
        (model_dir / "README.md").write_text("readme")
        (model_dir / "config.json").write_text("{}")

        models = storage.scan_local_models()

        assert models == []

    def test_scan_ignores_hidden_dirs(self, storage):
        """Test that scan ignores hidden directories."""
        hidden_dir = storage.models_dir / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "model" / "test.gguf").parent.mkdir(parents=True)
        (hidden_dir / "model" / "test.gguf").write_bytes(b"content")

        models = storage.scan_local_models()

        assert models == []

    def test_scan_includes_metadata(self, storage):
        """Test that scan includes metadata for known models."""
        # Create model
        model_dir = storage.models_dir / "author" / "model"
        model_dir.mkdir(parents=True)
        (model_dir / "model.gguf").write_bytes(b"content")

        # Add metadata
        storage.metadata["author/model"] = {
            "commit_sha": "abc123",
            "download_date": "2024-01-01",
        }

        models = storage.scan_local_models()

        assert len(models) == 1
        assert models[0]["commit_sha"] == "abc123"
        assert models[0]["download_date"] == "2024-01-01"


class TestGetModelPath:
    """Test suite for get_model_path method."""

    @pytest.fixture
    def storage(self):
        """Create a StorageManager instance."""
        tmpdir = tempfile.mkdtemp()
        models_dir = Path(tmpdir) / "models"
        metadata_file = Path(tmpdir) / ".metadata.json"
        storage = StorageManager(models_dir, metadata_file)
        yield storage
        shutil.rmtree(tmpdir)

    def test_get_model_path(self, storage):
        """Test getting model path."""
        path = storage.get_model_path("author/model-name")

        assert path == storage.models_dir / "author" / "model-name"


class TestDeleteModel:
    """Test suite for delete_model method."""

    @pytest.fixture
    def storage(self):
        """Create a StorageManager instance with a model."""
        tmpdir = tempfile.mkdtemp()
        models_dir = Path(tmpdir) / "models"
        metadata_file = Path(tmpdir) / ".metadata.json"
        storage = StorageManager(models_dir, metadata_file)

        # Create model
        model_dir = models_dir / "author" / "model"
        model_dir.mkdir(parents=True)
        (model_dir / "model.gguf").write_bytes(b"content")

        # Add metadata
        storage.metadata["author/model"] = {"commit_sha": "abc123"}
        storage._save_metadata()

        yield storage
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_delete_model_success(self, storage):
        """Test successful model deletion."""
        assert (storage.models_dir / "author" / "model").exists()
        assert "author/model" in storage.metadata

        result = storage.delete_model("author/model")

        assert result is True
        assert not (storage.models_dir / "author" / "model").exists()
        assert "author/model" not in storage.metadata

    def test_delete_nonexistent_model(self, storage):
        """Test deleting non-existent model."""
        result = storage.delete_model("nonexistent/model")

        assert result is True  # No error, just nothing to delete

    def test_delete_model_removes_metadata(self, storage):
        """Test that deletion removes metadata."""
        storage.delete_model("author/model")

        # Reload metadata from file
        with open(storage.metadata_file) as f:
            saved_metadata = json.load(f)

        assert "author/model" not in saved_metadata


class TestSaveModelMetadata:
    """Test suite for save_model_metadata method."""

    @pytest.fixture
    def storage(self):
        """Create a StorageManager instance."""
        tmpdir = tempfile.mkdtemp()
        models_dir = Path(tmpdir) / "models"
        metadata_file = Path(tmpdir) / ".metadata.json"
        storage = StorageManager(models_dir, metadata_file)
        yield storage
        shutil.rmtree(tmpdir)

    def test_save_new_metadata(self, storage):
        """Test saving metadata for new model."""
        storage.save_model_metadata("author/model", commit_sha="abc123")

        assert "author/model" in storage.metadata
        assert storage.metadata["author/model"]["commit_sha"] == "abc123"
        assert "download_date" in storage.metadata["author/model"]

    def test_save_metadata_with_additional_data(self, storage):
        """Test saving metadata with additional data."""
        storage.save_model_metadata(
            "author/model",
            commit_sha="abc123",
            additional_data={"custom_field": "value"},
        )

        assert storage.metadata["author/model"]["custom_field"] == "value"

    def test_save_metadata_updates_existing(self, storage):
        """Test updating existing metadata."""
        storage.save_model_metadata("author/model", commit_sha="old")
        storage.save_model_metadata("author/model", commit_sha="new")

        assert storage.metadata["author/model"]["commit_sha"] == "new"

    def test_save_metadata_persists_to_file(self, storage):
        """Test that metadata is persisted to file."""
        storage.save_model_metadata("author/model", commit_sha="abc123")

        # Reload from file
        with open(storage.metadata_file) as f:
            saved = json.load(f)

        assert saved["author/model"]["commit_sha"] == "abc123"


class TestGetModelMetadata:
    """Test suite for get_model_metadata method."""

    @pytest.fixture
    def storage(self):
        """Create a StorageManager instance."""
        tmpdir = tempfile.mkdtemp()
        models_dir = Path(tmpdir) / "models"
        metadata_file = Path(tmpdir) / ".metadata.json"
        storage = StorageManager(models_dir, metadata_file)
        yield storage
        shutil.rmtree(tmpdir)

    def test_get_existing_metadata(self, storage):
        """Test getting existing metadata."""
        storage.metadata["author/model"] = {"commit_sha": "abc123"}

        result = storage.get_model_metadata("author/model")

        assert result is not None
        assert result["commit_sha"] == "abc123"

    def test_get_nonexistent_metadata(self, storage):
        """Test getting non-existent metadata."""
        result = storage.get_model_metadata("nonexistent/model")

        assert result is None


class TestStorageUsage:
    """Test suite for storage usage methods."""

    @pytest.fixture
    def storage(self):
        """Create a StorageManager instance with files."""
        tmpdir = tempfile.mkdtemp()
        models_dir = Path(tmpdir) / "models"
        metadata_file = Path(tmpdir) / ".metadata.json"
        storage = StorageManager(models_dir, metadata_file)

        # Create some GGUF files
        model_dir = models_dir / "author" / "model"
        model_dir.mkdir(parents=True)
        (model_dir / "model.gguf").write_bytes(b"x" * 1024)  # 1KB

        yield storage
        shutil.rmtree(tmpdir)

    def test_get_storage_usage(self, storage):
        """Test getting storage usage."""
        used, total = storage.get_storage_usage()

        assert used == 1024  # 1KB from our test file
        assert total > 0  # Should have some disk space

    def test_get_available_space(self, storage):
        """Test getting available space."""
        available = storage.get_available_space()

        assert available > 0


class TestMetadataFileHandling:
    """Test suite for metadata file edge cases."""

    def test_load_corrupted_metadata(self):
        """Test loading corrupted metadata file."""
        tmpdir = tempfile.mkdtemp()
        try:
            models_dir = Path(tmpdir) / "models"
            metadata_file = Path(tmpdir) / ".metadata.json"

            # Create corrupted JSON
            metadata_file.write_text("not valid json {{{")

            storage = StorageManager(models_dir, metadata_file)

            assert storage.metadata == {}
        finally:
            shutil.rmtree(tmpdir)

    def test_save_creates_parent_dirs(self):
        """Test that save creates parent directories."""
        tmpdir = tempfile.mkdtemp()
        try:
            models_dir = Path(tmpdir) / "models"
            metadata_file = Path(tmpdir) / "subdir" / "deep" / ".metadata.json"

            storage = StorageManager(models_dir, metadata_file)
            storage.save_model_metadata("author/model", commit_sha="abc")

            assert metadata_file.exists()
        finally:
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
