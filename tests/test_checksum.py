"""Tests for checksum verification in downloader."""

import hashlib
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.downloader import DownloadManager


class TestChecksumCalculation:
    """Test suite for SHA256 checksum calculation."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def mock_hf_client(self):
        """Create a mock HuggingFace client."""
        client = Mock()
        client.get_file_sizes = Mock(return_value={"test.gguf": 1024})
        client.get_commit_sha = Mock(return_value="abc123")
        return client

    @pytest.fixture
    def mock_storage(self, temp_dir):
        """Create a mock storage manager."""
        storage = Mock()
        storage.get_model_path = Mock(return_value=temp_dir / "test_model")
        storage.save_model_metadata = Mock()
        storage.models_dir = temp_dir
        return storage

    @pytest.fixture
    def downloader(self, mock_hf_client, mock_storage):
        """Create a DownloadManager instance."""
        return DownloadManager(mock_hf_client, mock_storage)

    def test_calculate_sha256_small_file(self, downloader, temp_dir):
        """Test SHA256 calculation for small file."""
        test_file = temp_dir / "test.bin"
        test_content = b"Hello, World!"
        test_file.write_bytes(test_content)

        checksum = downloader._calculate_sha256(test_file)

        # Verify against known SHA256
        expected = hashlib.sha256(test_content).hexdigest()
        assert checksum == expected

    def test_calculate_sha256_large_file(self, downloader, temp_dir):
        """Test SHA256 calculation for larger file."""
        test_file = temp_dir / "large.bin"
        test_content = b"x" * (1024 * 1024)  # 1MB
        test_file.write_bytes(test_content)

        checksum = downloader._calculate_sha256(test_file)

        # Verify against known SHA256
        expected = hashlib.sha256(test_content).hexdigest()
        assert checksum == expected

    def test_calculate_sha256_empty_file(self, downloader, temp_dir):
        """Test SHA256 calculation for empty file."""
        test_file = temp_dir / "empty.bin"
        test_file.write_bytes(b"")

        checksum = downloader._calculate_sha256(test_file)

        # Verify against known SHA256 of empty string
        expected = hashlib.sha256(b"").hexdigest()
        assert checksum == expected

    def test_calculate_sha256_different_content(self, downloader, temp_dir):
        """Test that different content produces different checksums."""
        file1 = temp_dir / "file1.bin"
        file2 = temp_dir / "file2.bin"

        file1.write_bytes(b"content1")
        file2.write_bytes(b"content2")

        checksum1 = downloader._calculate_sha256(file1)
        checksum2 = downloader._calculate_sha256(file2)

        assert checksum1 != checksum2


class TestChecksumVerification:
    """Test suite for checksum verification."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def mock_hf_client(self):
        """Create a mock HuggingFace client."""
        client = Mock()
        client.get_file_sizes = Mock(return_value={"test.gguf": 1024})
        client.get_commit_sha = Mock(return_value="abc123")
        return client

    @pytest.fixture
    def mock_storage(self, temp_dir):
        """Create a mock storage manager."""
        storage = Mock()
        storage.get_model_path = Mock(return_value=temp_dir / "test_model")
        storage.save_model_metadata = Mock()
        storage.models_dir = temp_dir
        return storage

    @pytest.fixture
    def downloader(self, mock_hf_client, mock_storage):
        """Create a DownloadManager instance."""
        return DownloadManager(mock_hf_client, mock_storage)

    def test_verify_checksum_valid(self, downloader, temp_dir):
        """Test verification with matching checksum."""
        test_file = temp_dir / "test.bin"
        test_content = b"Test content"
        test_file.write_bytes(test_content)

        expected_checksum = hashlib.sha256(test_content).hexdigest()

        result = downloader._verify_checksum(test_file, expected_checksum)
        assert result is True

    def test_verify_checksum_mismatch(self, downloader, temp_dir):
        """Test verification with mismatching checksum."""
        test_file = temp_dir / "test.bin"
        test_file.write_bytes(b"Test content")

        wrong_checksum = hashlib.sha256(b"Wrong content").hexdigest()

        with pytest.raises(Exception) as exc_info:
            downloader._verify_checksum(test_file, wrong_checksum)

        assert "Checksum mismatch" in str(exc_info.value)

    def test_verify_checksum_none(self, downloader, temp_dir):
        """Test verification with None (skips verification)."""
        test_file = temp_dir / "test.bin"
        test_file.write_bytes(b"Test content")

        result = downloader._verify_checksum(test_file, None)
        assert result is True

    def test_verify_checksum_missing_file(self, downloader, temp_dir):
        """Test verification when file doesn't exist."""
        test_file = temp_dir / "nonexistent.bin"

        with pytest.raises(Exception) as exc_info:
            downloader._verify_checksum(test_file, "abc123")

        assert "File not found" in str(exc_info.value)


class TestChecksumIntegration:
    """Test suite for checksum verification in download workflow."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def mock_hf_client(self):
        """Create a mock HuggingFace client."""
        client = Mock()
        client.get_file_sizes = Mock(return_value={"test.gguf": 1024})
        client.get_commit_sha = Mock(return_value="abc123")
        return client

    @pytest.fixture
    def mock_storage(self, temp_dir):
        """Create a mock storage manager."""
        storage = Mock()
        storage.get_model_path = Mock(return_value=temp_dir / "test_model")
        storage.save_model_metadata = Mock()
        storage.models_dir = temp_dir
        return storage

    @pytest.fixture
    def downloader(self, mock_hf_client, mock_storage):
        """Create a DownloadManager instance."""
        return DownloadManager(mock_hf_client, mock_storage)

    @pytest.mark.asyncio
    async def test_download_verifies_checksum(self, downloader, temp_dir):
        """Test that download workflow verifies checksums."""
        repo_id = "test/model"
        files = ["test.gguf"]

        # Mock hf_hub_download to create a file
        def mock_download(repo_id, filename, local_dir):
            file_path = Path(local_dir) / filename
            file_path.write_bytes(b"x" * 1024)
            return str(file_path)

        # Track if _verify_checksum was called
        original_verify = downloader._verify_checksum
        verification_called = []

        def tracked_verify(file_path, expected):
            verification_called.append((file_path.name, expected))
            return original_verify(file_path, expected)

        downloader._verify_checksum = tracked_verify

        from unittest.mock import patch

        with patch("src.services.downloader.hf_hub_download", side_effect=mock_download):
            success = await downloader.download_model(repo_id, files)

        assert success is True
        # Verify should have been called for the downloaded file
        assert len(verification_called) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
