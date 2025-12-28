"""Tests for update checker."""

import pytest
from pathlib import Path
from unittest.mock import Mock

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.updater import UpdateChecker
from src.exceptions import NetworkError, HuggingFaceError


class TestUpdateCheckerInitialization:
    """Test suite for UpdateChecker initialization."""

    def test_initialization(self):
        """Test updater initializes with dependencies."""
        mock_hf_client = Mock()
        mock_storage = Mock()

        updater = UpdateChecker(mock_hf_client, mock_storage)

        assert updater.hf_client == mock_hf_client
        assert updater.storage == mock_storage


class TestCheckSingleModel:
    """Test suite for check_single_model method."""

    @pytest.fixture
    def updater(self):
        """Create an UpdateChecker with mocked dependencies."""
        mock_hf_client = Mock()
        mock_storage = Mock()
        return UpdateChecker(mock_hf_client, mock_storage)

    def test_check_model_up_to_date(self, updater):
        """Test checking model that is up to date."""
        updater.hf_client.get_commit_sha.return_value = "abc123def456"

        result = updater.check_single_model("author/model", "abc123def456")

        assert result == "up_to_date"
        updater.hf_client.get_commit_sha.assert_called_once_with("author/model")

    def test_check_model_update_available(self, updater):
        """Test checking model with update available."""
        updater.hf_client.get_commit_sha.return_value = "new_commit_sha"

        result = updater.check_single_model("author/model", "old_commit_sha")

        assert result == "update_available"

    def test_check_model_no_local_sha(self, updater):
        """Test checking model with no local SHA."""
        result = updater.check_single_model("author/model", None)

        assert result == "unknown"
        updater.hf_client.get_commit_sha.assert_not_called()

    def test_check_model_empty_local_sha(self, updater):
        """Test checking model with empty local SHA."""
        result = updater.check_single_model("author/model", "")

        assert result == "unknown"

    def test_check_model_no_remote_sha(self, updater):
        """Test checking model when remote SHA unavailable."""
        updater.hf_client.get_commit_sha.return_value = None

        result = updater.check_single_model("author/model", "local_sha")

        assert result == "error"

    def test_check_model_network_error(self, updater):
        """Test checking model with network error."""
        updater.hf_client.get_commit_sha.side_effect = NetworkError("Connection failed")

        result = updater.check_single_model("author/model", "local_sha")

        assert result == "error"

    def test_check_model_api_error(self, updater):
        """Test checking model with API error."""
        updater.hf_client.get_commit_sha.side_effect = HuggingFaceError("API error")

        result = updater.check_single_model("author/model", "local_sha")

        assert result == "error"

    def test_check_model_generic_exception(self, updater):
        """Test checking model with generic exception."""
        updater.hf_client.get_commit_sha.side_effect = Exception("Unknown error")

        result = updater.check_single_model("author/model", "local_sha")

        assert result == "error"


class TestCheckForUpdates:
    """Test suite for check_for_updates method."""

    @pytest.fixture
    def updater(self):
        """Create an UpdateChecker with mocked dependencies."""
        mock_hf_client = Mock()
        mock_storage = Mock()
        return UpdateChecker(mock_hf_client, mock_storage)

    def test_check_multiple_models(self, updater):
        """Test checking multiple models at once."""
        models = [
            {"repo_id": "author1/model1", "commit_sha": "sha1"},
            {"repo_id": "author2/model2", "commit_sha": "sha2"},
        ]

        # First model up to date, second has update
        updater.hf_client.get_commit_sha.side_effect = ["sha1", "new_sha"]

        results = updater.check_for_updates(models)

        assert len(results) == 2
        assert results["author1/model1"] == "up_to_date"
        assert results["author2/model2"] == "update_available"

    def test_check_empty_list(self, updater):
        """Test checking empty model list."""
        results = updater.check_for_updates([])

        assert results == {}

    def test_check_mixed_results(self, updater):
        """Test checking models with mixed results."""
        models = [
            {"repo_id": "author1/model1", "commit_sha": "sha1"},
            {"repo_id": "author2/model2", "commit_sha": None},  # Unknown
            {"repo_id": "author3/model3", "commit_sha": "sha3"},
        ]

        updater.hf_client.get_commit_sha.side_effect = [
            "sha1",  # Up to date
            Exception("API error"),  # Error
        ]

        results = updater.check_for_updates(models)

        assert results["author1/model1"] == "up_to_date"
        assert results["author2/model2"] == "unknown"
        assert results["author3/model3"] == "error"

    def test_check_models_without_commit_sha_key(self, updater):
        """Test checking models without commit_sha key."""
        models = [
            {"repo_id": "author/model"},  # No commit_sha key
        ]

        results = updater.check_for_updates(models)

        assert results["author/model"] == "unknown"


class TestUpdateStatusEdgeCases:
    """Test edge cases for update checking."""

    @pytest.fixture
    def updater(self):
        """Create an UpdateChecker with mocked dependencies."""
        mock_hf_client = Mock()
        mock_storage = Mock()
        return UpdateChecker(mock_hf_client, mock_storage)

    def test_case_sensitive_sha_comparison(self, updater):
        """Test that SHA comparison is case-sensitive."""
        updater.hf_client.get_commit_sha.return_value = "ABC123"

        result = updater.check_single_model("author/model", "abc123")

        # Should be update available since SHAs are case-sensitive
        assert result == "update_available"

    def test_sha_partial_match(self, updater):
        """Test that partial SHA match doesn't count as up-to-date."""
        updater.hf_client.get_commit_sha.return_value = "abc123def456"

        result = updater.check_single_model("author/model", "abc123")

        assert result == "update_available"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
