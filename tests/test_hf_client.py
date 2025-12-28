"""Tests for HuggingFace client."""

import time
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.hf_client import HuggingFaceClient
from src.exceptions import HuggingFaceError, NetworkError


class TestHuggingFaceClientInitialization:
    """Test suite for HuggingFaceClient initialization."""

    def test_initialization_default_cache_duration(self):
        """Test client initializes with default cache duration."""
        client = HuggingFaceClient()
        assert client._cache_duration == 300
        assert client._cache == {}
        assert client.api is not None

    def test_initialization_custom_cache_duration(self):
        """Test client initializes with custom cache duration."""
        client = HuggingFaceClient(cache_duration=600)
        assert client._cache_duration == 600


class TestHuggingFaceClientCaching:
    """Test suite for caching functionality."""

    def test_cache_set_and_get(self):
        """Test setting and getting cached values."""
        client = HuggingFaceClient()
        client._set_cache("test_key", {"data": "value"})

        hit, value = client._get_cached("test_key")
        assert hit is True
        assert value == {"data": "value"}

    def test_cache_miss(self):
        """Test cache miss for non-existent key."""
        client = HuggingFaceClient()
        hit, value = client._get_cached("nonexistent")
        assert hit is False
        assert value is None

    def test_cache_expiry(self):
        """Test cache expires after duration."""
        client = HuggingFaceClient(cache_duration=0)  # Expire immediately
        client._set_cache("test_key", "value")

        # Wait a tiny bit to ensure expiry
        time.sleep(0.01)

        hit, value = client._get_cached("test_key")
        assert hit is False
        assert value is None

    def test_clear_cache(self):
        """Test clearing the cache."""
        client = HuggingFaceClient()
        client._set_cache("key1", "value1")
        client._set_cache("key2", "value2")

        assert len(client._cache) == 2
        client.clear_cache()
        assert len(client._cache) == 0

    def test_cache_stats(self):
        """Test cache statistics."""
        client = HuggingFaceClient()
        client._set_cache("key1", "value1")
        client._set_cache("key2", "value2")

        stats = client.get_cache_stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 2


class TestSearchModels:
    """Test suite for search_models method."""

    @pytest.fixture
    def mock_client(self):
        """Create a client with mocked API."""
        client = HuggingFaceClient()
        client.api = Mock()
        return client

    def test_search_models_success(self, mock_client):
        """Test successful model search."""
        mock_model = Mock()
        mock_model.id = "author/model-name"
        mock_model.author = "author"
        mock_model.downloads = 1000
        mock_model.likes = 50
        mock_model.lastModified = "2024-01-01"
        mock_model.cardData = {"description": "Test model"}
        mock_model.tags = ["gguf", "llama"]

        mock_client.api.list_models.return_value = [mock_model]

        results = mock_client.search_models("llama", limit=10)

        assert len(results) == 1
        assert results[0]["repo_id"] == "author/model-name"
        assert results[0]["author"] == "author"
        assert results[0]["downloads"] == 1000
        mock_client.api.list_models.assert_called_once_with(
            search="llama", filter="gguf", limit=10, sort="downloads", direction=-1
        )

    def test_search_models_caching(self, mock_client):
        """Test search results are cached."""
        mock_model = Mock()
        mock_model.id = "author/model"
        mock_model.author = "author"
        mock_model.downloads = 100
        mock_model.likes = 10
        mock_model.lastModified = None
        mock_model.cardData = None
        mock_model.tags = []

        mock_client.api.list_models.return_value = [mock_model]

        # First call
        results1 = mock_client.search_models("test", limit=50)
        # Second call - should use cache
        results2 = mock_client.search_models("test", limit=50)

        assert results1 == results2
        # API should only be called once due to caching
        assert mock_client.api.list_models.call_count == 1

    def test_search_models_empty_results(self, mock_client):
        """Test empty search results."""
        mock_client.api.list_models.return_value = []

        results = mock_client.search_models("nonexistent")

        assert results == []

    def test_search_models_network_error(self, mock_client):
        """Test network error during search."""
        mock_client.api.list_models.side_effect = OSError("Connection refused")

        with pytest.raises(NetworkError):
            mock_client.search_models("test")

    def test_search_models_api_error(self, mock_client):
        """Test API error during search."""
        mock_client.api.list_models.side_effect = Exception("API error")

        with pytest.raises(HuggingFaceError):
            mock_client.search_models("test")


class TestGetModelInfo:
    """Test suite for get_model_info method."""

    @pytest.fixture
    def mock_client(self):
        """Create a client with mocked API."""
        client = HuggingFaceClient()
        client.api = Mock()
        return client

    def test_get_model_info_success(self, mock_client):
        """Test successful model info retrieval."""
        mock_model = Mock()
        mock_model.id = "author/model"
        mock_model.author = "author"
        mock_model.downloads = 500
        mock_model.likes = 25
        mock_model.lastModified = "2024-01-01"
        mock_model.cardData = None
        mock_model.tags = ["gguf"]

        mock_client.api.model_info.return_value = mock_model

        result = mock_client.get_model_info("author/model")

        assert result is not None
        assert result["repo_id"] == "author/model"
        assert result["downloads"] == 500

    def test_get_model_info_caching(self, mock_client):
        """Test model info is cached."""
        mock_model = Mock()
        mock_model.id = "author/model"
        mock_model.author = "author"
        mock_model.downloads = 100
        mock_model.likes = 10
        mock_model.lastModified = None
        mock_model.cardData = None
        mock_model.tags = []

        mock_client.api.model_info.return_value = mock_model

        # First call
        mock_client.get_model_info("author/model")
        # Second call - should use cache
        mock_client.get_model_info("author/model")

        assert mock_client.api.model_info.call_count == 1

    def test_get_model_info_network_error(self, mock_client):
        """Test network error during model info fetch."""
        mock_client.api.model_info.side_effect = OSError("Timeout")

        with pytest.raises(NetworkError):
            mock_client.get_model_info("author/model")

    def test_get_model_info_api_error(self, mock_client):
        """Test API error during model info fetch."""
        mock_client.api.model_info.side_effect = Exception("Not found")

        with pytest.raises(HuggingFaceError):
            mock_client.get_model_info("author/model")


class TestListGgufFiles:
    """Test suite for list_gguf_files method."""

    @pytest.fixture
    def mock_client(self):
        """Create a client with mocked API."""
        client = HuggingFaceClient()
        client.api = Mock()
        return client

    def test_list_gguf_files_success(self, mock_client):
        """Test successful GGUF file listing."""
        mock_client.api.list_repo_files.return_value = [
            "model.gguf",
            "model-Q4_K_M.gguf",
            "README.md",
            "config.json",
            "tokenizer.json",
        ]

        files = mock_client.list_gguf_files("author/model")

        assert len(files) == 2
        assert "model.gguf" in files
        assert "model-Q4_K_M.gguf" in files
        assert "README.md" not in files

    def test_list_gguf_files_case_insensitive(self, mock_client):
        """Test GGUF extension matching is case-insensitive."""
        mock_client.api.list_repo_files.return_value = [
            "model.GGUF",
            "model2.Gguf",
            "model3.gguf",
        ]

        files = mock_client.list_gguf_files("author/model")

        assert len(files) == 3

    def test_list_gguf_files_empty(self, mock_client):
        """Test empty file list."""
        mock_client.api.list_repo_files.return_value = ["README.md", "config.json"]

        files = mock_client.list_gguf_files("author/model")

        assert files == []

    def test_list_gguf_files_caching(self, mock_client):
        """Test file listing is cached."""
        mock_client.api.list_repo_files.return_value = ["model.gguf"]

        mock_client.list_gguf_files("author/model")
        mock_client.list_gguf_files("author/model")

        assert mock_client.api.list_repo_files.call_count == 1

    def test_list_gguf_files_network_error(self, mock_client):
        """Test network error during file listing."""
        mock_client.api.list_repo_files.side_effect = OSError("Connection reset")

        with pytest.raises(NetworkError):
            mock_client.list_gguf_files("author/model")


class TestGetFileSizes:
    """Test suite for get_file_sizes method."""

    @pytest.fixture
    def mock_client(self):
        """Create a client with mocked API."""
        client = HuggingFaceClient()
        client.api = Mock()
        return client

    def test_get_file_sizes_success(self, mock_client):
        """Test successful file size retrieval."""
        mock_sibling1 = Mock()
        mock_sibling1.rfilename = "model.gguf"
        mock_sibling1.size = 1024 * 1024 * 100  # 100 MB

        mock_sibling2 = Mock()
        mock_sibling2.rfilename = "README.md"
        mock_sibling2.size = 1024

        mock_model_info = Mock()
        mock_model_info.siblings = [mock_sibling1, mock_sibling2]

        mock_client.api.model_info.return_value = mock_model_info

        sizes = mock_client.get_file_sizes("author/model")

        assert sizes["model.gguf"] == 1024 * 1024 * 100
        assert sizes["README.md"] == 1024

    def test_get_file_sizes_missing_size(self, mock_client):
        """Test handling of missing size attribute."""
        mock_sibling = Mock(spec=["rfilename"])  # No size attribute
        mock_sibling.rfilename = "model.gguf"

        mock_model_info = Mock()
        mock_model_info.siblings = [mock_sibling]

        mock_client.api.model_info.return_value = mock_model_info

        sizes = mock_client.get_file_sizes("author/model")

        assert sizes["model.gguf"] == 0

    def test_get_file_sizes_none_size(self, mock_client):
        """Test handling of None size."""
        mock_sibling = Mock()
        mock_sibling.rfilename = "model.gguf"
        mock_sibling.size = None

        mock_model_info = Mock()
        mock_model_info.siblings = [mock_sibling]

        mock_client.api.model_info.return_value = mock_model_info

        sizes = mock_client.get_file_sizes("author/model")

        assert sizes["model.gguf"] == 0

    def test_get_file_sizes_caching(self, mock_client):
        """Test file sizes are cached."""
        mock_sibling = Mock()
        mock_sibling.rfilename = "model.gguf"
        mock_sibling.size = 1024

        mock_model_info = Mock()
        mock_model_info.siblings = [mock_sibling]

        mock_client.api.model_info.return_value = mock_model_info

        mock_client.get_file_sizes("author/model")
        mock_client.get_file_sizes("author/model")

        assert mock_client.api.model_info.call_count == 1

    def test_get_file_sizes_network_error(self, mock_client):
        """Test network error during file size fetch."""
        mock_client.api.model_info.side_effect = OSError("DNS error")

        with pytest.raises(NetworkError):
            mock_client.get_file_sizes("author/model")


class TestGetCommitSha:
    """Test suite for get_commit_sha method."""

    @pytest.fixture
    def mock_client(self):
        """Create a client with mocked API."""
        client = HuggingFaceClient()
        client.api = Mock()
        return client

    def test_get_commit_sha_success(self, mock_client):
        """Test successful commit SHA retrieval."""
        mock_model_info = Mock()
        mock_model_info.sha = "abc123def456"

        mock_client.api.model_info.return_value = mock_model_info

        sha = mock_client.get_commit_sha("author/model")

        assert sha == "abc123def456"

    def test_get_commit_sha_no_sha(self, mock_client):
        """Test handling of missing SHA attribute."""
        mock_model_info = Mock(spec=[])  # No sha attribute

        mock_client.api.model_info.return_value = mock_model_info

        sha = mock_client.get_commit_sha("author/model")

        assert sha is None

    def test_get_commit_sha_not_cached(self, mock_client):
        """Test commit SHA is NOT cached (intentional for update checks)."""
        mock_model_info = Mock()
        mock_model_info.sha = "abc123"

        mock_client.api.model_info.return_value = mock_model_info

        mock_client.get_commit_sha("author/model")
        mock_client.get_commit_sha("author/model")

        # Should be called twice since we don't cache commit SHAs
        assert mock_client.api.model_info.call_count == 2

    def test_get_commit_sha_network_error(self, mock_client):
        """Test network error during SHA fetch."""
        mock_client.api.model_info.side_effect = OSError("Network unreachable")

        with pytest.raises(NetworkError):
            mock_client.get_commit_sha("author/model")


class TestExtractModelData:
    """Test suite for _extract_model_data method."""

    def test_extract_model_data_full(self):
        """Test extraction with all fields present."""
        client = HuggingFaceClient()

        mock_model = Mock()
        mock_model.id = "author/model-name"
        mock_model.author = "author"
        mock_model.downloads = 1000
        mock_model.likes = 50
        mock_model.lastModified = "2024-01-01T00:00:00Z"
        mock_model.cardData = {"description": "A test model"}
        mock_model.tags = ["gguf", "llama", "7b"]

        result = client._extract_model_data(mock_model)

        assert result is not None
        assert result["repo_id"] == "author/model-name"
        assert result["author"] == "author"
        assert result["name"] == "model-name"
        assert result["downloads"] == 1000
        assert result["likes"] == 50
        assert result["description"] == "A test model"
        assert "gguf" in result["tags"]

    def test_extract_model_data_minimal(self):
        """Test extraction with minimal fields."""
        client = HuggingFaceClient()

        mock_model = Mock()
        mock_model.id = "author/model"
        mock_model.author = None
        mock_model.downloads = None
        mock_model.likes = None
        mock_model.lastModified = None
        mock_model.cardData = None
        mock_model.tags = None

        result = client._extract_model_data(mock_model)

        assert result is not None
        assert result["repo_id"] == "author/model"
        assert result["author"] == "author"  # Derived from ID
        assert result["downloads"] == 0
        assert result["likes"] == 0
        assert result["description"] == ""
        assert result["tags"] == []

    def test_extract_model_data_invalid_card_data(self):
        """Test extraction with invalid cardData type."""
        client = HuggingFaceClient()

        mock_model = Mock()
        mock_model.id = "author/model"
        mock_model.author = "author"
        mock_model.downloads = 0
        mock_model.likes = 0
        mock_model.lastModified = None
        mock_model.cardData = "not a dict"  # Invalid type
        mock_model.tags = []

        result = client._extract_model_data(mock_model)

        assert result is not None
        assert result["description"] == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
