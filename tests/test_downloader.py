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
        storage.models_dir = temp_dir  # Add models_dir for disk usage checks
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
        assert callback_data["status"] == "downloading"
        assert callback_data["initial_bytes"] == 0  # No initial bytes in this test

    def test_progress_data_resumed_download(self, downloader):
        """Test progress data for resumed download."""
        callback_data = None

        def callback(data):
            nonlocal callback_data
            callback_data = data

        # Mark as resuming to trigger proper status
        downloader._is_resuming = True
        downloader._initial_bytes_before = 1024 * 1024

        # Simulate resumed download (started with 1MB already downloaded)
        downloader._send_progress(
            callback,
            "test/model",
            "test.gguf",
            1,
            1,
            1024 * 1024,  # 1MB
            1024 * 1024 * 10,  # 10MB total
            1024 * 1024,  # 1MB overall
            1024 * 1024 * 10,
            2.0,  # 2 seconds elapsed (first file, early in session)
        )

        assert callback_data is not None
        assert callback_data["status"] == "resuming"
        assert callback_data["initial_bytes"] == 1024 * 1024

    def test_cancel_download(self, downloader):
        """Test download cancellation."""
        assert not downloader._cancelled
        downloader.cancel_download()
        assert downloader._cancelled

    @pytest.mark.asyncio
    async def test_heartbeat_progress_when_size_unchanged(self, downloader):
        """Test that heartbeat sends progress even when file size doesn't change.

        This tests the fix for UnboundLocalError when overall_downloaded
        was referenced in the heartbeat path before being defined.

        The bug occurred when:
        1. Monitoring loop starts
        2. current_size = 0, last_reported_size = 0 (size_changed = False)
        3. time_since_update >= 0.5 (heartbeat triggers)
        4. Heartbeat path tries to use overall_downloaded before it was defined

        Fix: Calculate overall_downloaded BEFORE if/elif blocks.
        """
        # Test the helper method directly
        # This ensures overall_downloaded is calculated correctly
        overall_downloaded, new_bytes = downloader._calculate_overall_downloaded(
            current_size=0, initial_incomplete_size=0, overall_downloaded_before=0
        )

        assert overall_downloaded == 0
        assert new_bytes == 0

        # Test with some progress
        overall_downloaded, new_bytes = downloader._calculate_overall_downloaded(
            current_size=1024, initial_incomplete_size=512, overall_downloaded_before=2048
        )

        assert new_bytes == 512  # 1024 - 512
        assert overall_downloaded == 3072  # 2048 + 512 + 512

    @pytest.mark.asyncio
    async def test_resumed_download_calculation_accuracy(self, downloader):
        """Test that resumed download overall_downloaded calculation is accurate.

        When resuming a download:
        - initial_incomplete_size should be the size of existing file
        - new_bytes_this_session should only count bytes downloaded THIS session
        - overall_downloaded should not double-count resumed bytes
        """
        # Scenario: Resume with 1GB already downloaded
        initial_incomplete_size = 1024 * 1024 * 1024  # 1GB
        overall_downloaded_before = 0  # First file

        # After downloading 500MB more THIS session
        current_size = initial_incomplete_size + (500 * 1024 * 1024)

        overall_downloaded, new_bytes = downloader._calculate_overall_downloaded(
            current_size=current_size,
            initial_incomplete_size=initial_incomplete_size,
            overall_downloaded_before=overall_downloaded_before,
        )

        expected_new_bytes = 500 * 1024 * 1024  # Only new bytes this session
        expected_overall = initial_incomplete_size + expected_new_bytes

        assert new_bytes == expected_new_bytes
        assert overall_downloaded == expected_overall

    @pytest.mark.asyncio
    async def test_calculate_overall_downloaded_multiple_files(self, downloader):
        """Test overall_downloaded calculation across multiple files."""
        # File 1 complete: 1GB
        # File 2 in progress: 500MB of 2GB (initial: 100MB, new: 400MB)

        file1_size = 1024 * 1024 * 1024  # 1GB
        file2_initial = 100 * 1024 * 1024  # 100MB already downloaded
        file2_current = 500 * 1024 * 1024  # 500MB total now

        overall_downloaded, new_bytes = downloader._calculate_overall_downloaded(
            current_size=file2_current,
            initial_incomplete_size=file2_initial,
            overall_downloaded_before=file1_size,
        )

        expected_new_bytes = file2_current - file2_initial  # 400MB
        expected_overall = file1_size + file2_initial + expected_new_bytes  # 1.5GB

        assert new_bytes == expected_new_bytes
        assert overall_downloaded == expected_overall

    @pytest.mark.asyncio
    async def test_download_monitoring_before_file_appears(self, downloader):
        """Test that monitoring handles case when incomplete file doesn't exist initially.

        This can happen when:
        1. Download starts in background thread
        2. Monitoring loop starts immediately
        3. HF hasn't created .incomplete file yet

        Should gracefully handle missing file and update when it appears.
        """
        # Test calculation when current_size is 0 (file not found yet)
        overall_downloaded, new_bytes = downloader._calculate_overall_downloaded(
            current_size=0,
            initial_incomplete_size=0,
            overall_downloaded_before=1024 * 1024,  # 1MB from previous file
        )

        # Should still return valid values
        assert new_bytes == 0
        assert overall_downloaded == 1024 * 1024  # Just previous file

        # When file appears with 512KB
        overall_downloaded, new_bytes = downloader._calculate_overall_downloaded(
            current_size=512 * 1024,
            initial_incomplete_size=0,
            overall_downloaded_before=1024 * 1024,
        )

        assert new_bytes == 512 * 1024
        assert overall_downloaded == 1024 * 1024 + 512 * 1024

    def test_calculate_overall_downloaded_edge_cases(self, downloader):
        """Test edge cases for overall_downloaded calculation."""
        # Edge case 1: No download yet
        overall, new = downloader._calculate_overall_downloaded(0, 0, 0)
        assert overall == 0
        assert new == 0

        # Edge case 2: Fresh download (no resume)
        overall, new = downloader._calculate_overall_downloaded(1024, 0, 0)
        assert overall == 1024
        assert new == 1024

        # Edge case 3: Resume where current_size equals initial (no new progress)
        overall, new = downloader._calculate_overall_downloaded(512, 512, 0)
        assert overall == 512
        assert new == 0

        # Edge case 4: Large numbers (multi-GB files)
        large_size = 50 * 1024 * 1024 * 1024  # 50GB
        overall, new = downloader._calculate_overall_downloaded(large_size, 0, large_size * 2)
        assert overall == large_size * 3
        assert new == large_size


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
