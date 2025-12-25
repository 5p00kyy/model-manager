"""Local storage management for downloaded models."""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manages local model storage and metadata.

    Handles model file organization, metadata persistence, and storage operations.
    Models are organized in a directory structure: models/author/model_name/

    Attributes:
        models_dir: Root directory for storing downloaded models
        metadata_file: JSON file storing model metadata
        metadata: In-memory metadata dictionary
    """

    def __init__(self, models_dir: Path, metadata_file: Path) -> None:
        """
        Initialize storage manager.

        Creates the models directory if it doesn't exist and loads existing metadata.

        Args:
            models_dir: Directory where models are stored
            metadata_file: Path to metadata JSON file
        """
        self.models_dir: Path = models_dir
        self.metadata_file: Path = metadata_file
        self.models_dir.mkdir(exist_ok=True)

        # Load or initialize metadata
        self.metadata: dict[str, dict[str, Any]] = self._load_metadata()

    def scan_local_models(self) -> list[dict[str, Any]]:
        """
        Scan the models directory and return all downloaded models.

        Traverses the directory structure to find GGUF files and collects
        metadata for each model.

        Returns:
            List of dictionaries containing model information including repo_id,
            path, files, total_size, download_date, commit_sha, and update_status.
        """
        models = []

        if not self.models_dir.exists():
            return models

        # Scan directory structure: models/author/model_name/
        for author_dir in self.models_dir.iterdir():
            if not author_dir.is_dir() or author_dir.name.startswith("."):
                continue

            for model_dir in author_dir.iterdir():
                if not model_dir.is_dir():
                    continue

                repo_id = f"{author_dir.name}/{model_dir.name}"
                gguf_files = [f.name for f in model_dir.iterdir() if f.name.endswith(".gguf")]

                if not gguf_files:
                    continue

                # Get total size
                total_size = sum(
                    f.stat().st_size for f in model_dir.iterdir() if f.name.endswith(".gguf")
                )

                # Get metadata for this model
                meta = self.metadata.get(repo_id, {})

                models.append(
                    {
                        "repo_id": repo_id,
                        "path": str(model_dir),
                        "files": sorted(gguf_files),
                        "total_size": total_size,
                        "download_date": meta.get("download_date"),
                        "commit_sha": meta.get("commit_sha"),
                        "update_status": "unknown",
                    }
                )

        logger.info(f"Found {len(models)} local models")
        return models

    def get_model_path(self, repo_id: str) -> Path:
        """
        Get the path where a model should be stored.

        Args:
            repo_id: Repository ID

        Returns:
            Path to model directory
        """
        return self.models_dir / repo_id

    def delete_model(self, repo_id: str) -> bool:
        """
        Delete a model from local storage.

        Args:
            repo_id: Repository ID

        Returns:
            True if successful, False otherwise
        """
        try:
            model_path = self.get_model_path(repo_id)
            if model_path.exists():
                shutil.rmtree(model_path)
                logger.info(f"Deleted model: {repo_id}")

            # Remove from metadata
            if repo_id in self.metadata:
                del self.metadata[repo_id]
                self._save_metadata()

            return True
        except Exception as e:
            logger.error(f"Error deleting model {repo_id}: {e}")
            return False

    def save_model_metadata(
        self,
        repo_id: str,
        commit_sha: str | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Save metadata for a downloaded model.

        Args:
            repo_id: Repository ID
            commit_sha: Commit SHA of downloaded version
            additional_data: Additional metadata to store
        """
        if repo_id not in self.metadata:
            self.metadata[repo_id] = {}

        self.metadata[repo_id]["download_date"] = datetime.now().isoformat()

        if commit_sha:
            self.metadata[repo_id]["commit_sha"] = commit_sha

        if additional_data:
            self.metadata[repo_id].update(additional_data)

        self._save_metadata()
        logger.info(f"Saved metadata for {repo_id}")

    def get_model_metadata(self, repo_id: str) -> dict[str, Any] | None:
        """
        Get metadata for a specific model.

        Args:
            repo_id: Repository ID

        Returns:
            Metadata dictionary or None if not found
        """
        return self.metadata.get(repo_id)

    def get_storage_usage(self) -> tuple[int, int]:
        """
        Get storage usage information.

        Calculates space used by GGUF files and total disk space.

        Returns:
            Tuple of (used_bytes, total_bytes)
        """
        try:
            # Calculate used space
            used = 0
            if self.models_dir.exists():
                for item in self.models_dir.rglob("*.gguf"):
                    used += item.stat().st_size

            # Get total disk space
            stat = shutil.disk_usage(self.models_dir)
            return (used, stat.total)
        except Exception as e:
            logger.error(f"Error getting storage usage: {e}")
            return (0, 0)

    def get_available_space(self) -> int:
        """
        Get available disk space in bytes.

        Returns:
            Number of available bytes on disk
        """
        try:
            stat = shutil.disk_usage(self.models_dir)
            return stat.free
        except Exception as e:
            logger.error(f"Error getting available space: {e}")
            return 0

    def _load_metadata(self) -> dict[str, dict[str, Any]]:
        """
        Load metadata from JSON file.

        Returns:
            Dictionary of model metadata, empty dict if file doesn't exist
        """
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
                return {}
        return {}

    def _save_metadata(self):
        """Save metadata to file."""
        try:
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
