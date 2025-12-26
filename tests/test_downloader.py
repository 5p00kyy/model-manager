"""Tests for download manager."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import shutil

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.downloader import DownloadManager
from src.utils.helpers import ProgressData, DownloadSpeedCalculator, calculate_eta


class TestDownloadManager:
    """Test suite for DownloadManager."""

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
        return storage

    @pytest.fixture
    def downloader(self, mock_hf_client, mock_storage):
        """Create a DownloadManager instance."""
        return DownloadManager(mock_hf_client, mock_storage)

    def test_initialization(self, downloader):
        """Test DownloadManager initialization."""
        assert downloader is not None
        assert not downloader._cancelled
        assert downloader._executor is not None

    @pytest.mark.asyncio
    async def test_validate_download_success(self, downloader):
        """Test successful download validation."""
        valid, msg = await downloader.validate_download("test/model", ["test.gguf"], 1024)
        assert valid is True
        assert msg == ""

    @pytest.mark.asyncio
    async def test_validate_download_no_files(self, downloader):
        """Test validation with no files."""
        valid, msg = await downloader.validate_download("test/model", [], 0)
        assert valid is False
        assert "No files specified" in msg

    @pytest.mark.asyncio
    async def test_validate_download_invalid_repo(self, downloader):
        """Test validation with invalid repo ID."""
        valid, msg = await downloader.validate_download("invalid", ["test.gguf"], 1024)
        assert valid is False
        assert "Invalid repository ID" in msg

    @pytest.mark.asyncio
    async def test_validate_download_insufficient_space(self, downloader):
        """Test validation with insufficient disk space."""
        # Use a huge file size that's definitely larger than available space
        valid, msg = await downloader.validate_download("test/model", ["test.gguf"], 10**15)  # 1 PB
        assert valid is False
        assert "Insufficient disk space" in msg

    def test_progress_data_structure(self, downloader):
        """Test progress callback data structure."""
        callback_data = None

        def callback(data):
            nonlocal callback_data
            callback_data = data

        downloader._send_progress(
            callback,
            "test/model",
            "test.gguf",
            1,
            1,
            512,
            1024,
            512,
            1024,
            0.0,
        )

        assert callback_data is not None
        assert callback_data["repo_id"] == "test/model"
        assert callback_data["current_file"] == "test.gguf"
        assert callback_data["current_file_downloaded"] == 512
        assert callback_data["current_file_total"] == 1024
        assert callback_data["overall_downloaded"] == 512
        assert callback_data["overall_total"] == 1024

    def test_cancel_download(self, downloader):
        """Test download cancellation."""
        assert not downloader._cancelled
        downloader.cancel_download()
        assert downloader._cancelled


class TestProgressCalculations:
    """Test progress calculation logic."""

    def test_speed_calculation(self):
        """Test download speed calculation."""
        # Simulate 1 MB downloaded in 1 second
        overall_downloaded = 1024 * 1024
        elapsed = 1.0
        speed = overall_downloaded / elapsed if elapsed > 0 else 0
        assert speed == 1024 * 1024  # 1 MB/s

    def test_eta_calculation(self):
        """Test ETA calculation."""
        total_size = 1024 * 1024 * 100  # 100 MB
        downloaded = 1024 * 1024 * 25  # 25 MB
        speed = 1024 * 1024  # 1 MB/s

        remaining = total_size - downloaded
        eta = calculate_eta(remaining, speed)

        assert eta == 75  # 75 seconds remaining

    def test_eta_calculation_zero_speed(self):
        """Test ETA calculation with zero speed."""
        remaining = 1024 * 1024
        speed = 0
        eta = calculate_eta(remaining, speed)
        assert eta == 0  # Unknown ETA


class TestDownloadSpeedCalculator:
    """Test speed calculator with moving window average."""

    def test_speed_calculator_initialization(self):
        """Test speed calculator initialization."""
        calc = DownloadSpeedCalculator(window_size=10)
        assert calc.window_size == 10
        assert len(calc.samples) == 0

    def test_speed_calculator_single_sample(self):
        """Test speed calculator with single sample."""
        calc = DownloadSpeedCalculator()
        speed = calc.update(1024)
        assert speed == 0.0  # Need at least 2 samples

    def test_speed_calculator_multiple_samples(self):
        """Test speed calculator with multiple samples."""
        import time

        calc = DownloadSpeedCalculator(window_size=5)

        # Simulate downloading 1 KB per update with small delays
        bytes_downloaded = 0
        speed = 0.0
        for i in range(5):
            bytes_downloaded += 1024
            speed = calc.update(bytes_downloaded)
            time.sleep(0.01)  # Small delay between updates

        # Speed should be positive (bytes per second)
        assert speed > 0

    def test_speed_calculator_window_size(self):
        """Test that speed calculator maintains window size."""
        calc = DownloadSpeedCalculator(window_size=3)

        # Add more samples than window size
        for i in range(10):
            calc.update(i * 1024)

        # Should only keep last 3 samples
        assert len(calc.samples) <= 3

    def test_speed_calculator_reset(self):
        """Test speed calculator reset."""
        calc = DownloadSpeedCalculator()
        calc.update(1024)
        calc.update(2048)
        assert len(calc.samples) > 0

        calc.reset()
        assert len(calc.samples) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
