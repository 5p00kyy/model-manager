"""Update checker for local models."""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class UpdateChecker:
    """Check for updates to downloaded models."""

    def __init__(self, hf_client, storage_manager):
        """
        Initialize update checker.

        Args:
            hf_client: HuggingFaceClient instance
            storage_manager: StorageManager instance
        """
        self.hf_client = hf_client
        self.storage = storage_manager

    def check_for_updates(self, models: List[dict]) -> Dict[str, str]:
        """
        Check for updates for multiple models.

        Args:
            models: List of local model dicts

        Returns:
            Dict mapping repo_id to update status:
            - 'up_to_date': No update available
            - 'update_available': Update available
            - 'error': Error checking
            - 'unknown': No local commit SHA
        """
        results = {}

        for model in models:
            repo_id = model["repo_id"]
            status = self.check_single_model(repo_id, model.get("commit_sha"))
            results[repo_id] = status

        return results

    def check_single_model(self, repo_id: str, local_sha: Optional[str]) -> str:
        """
        Check if a single model has updates.

        Args:
            repo_id: Repository ID
            local_sha: Local commit SHA (None if unknown)

        Returns:
            Update status string
        """
        if not local_sha:
            return "unknown"

        try:
            remote_sha = self.hf_client.get_commit_sha(repo_id)

            if not remote_sha:
                logger.warning(f"Could not get remote SHA for {repo_id}")
                return "error"

            if remote_sha == local_sha:
                logger.info(f"{repo_id} is up to date")
                return "up_to_date"
            else:
                logger.info(
                    f"{repo_id} has update available "
                    f"(local: {local_sha[:8]}, remote: {remote_sha[:8]})"
                )
                return "update_available"

        except Exception as e:
            logger.error(f"Error checking updates for {repo_id}: {e}")
            return "error"
