"""Tests for download history tracking."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.download_history import DownloadHistory, DownloadRecord


class TestDownloadRecord:
    """Test suite for DownloadRecord dataclass."""

    def test_record_creation(self):
        """Test creating a download record."""
        record = DownloadRecord(
            repo_id="test/model",
            files=["file.gguf"],
            total_size=1024,
            start_time=datetime.now(),
        )
        assert record.repo_id == "test/model"
        assert record.status == "pending"
        assert record.bytes_downloaded == 0

    def test_record_to_dict(self):
        """Test converting record to dictionary."""
        record = DownloadRecord(
            repo_id="test/model",
            files=["file.gguf"],
            total_size=1024,
            start_time=datetime.now(),
        )
        data = record.to_dict()
        assert data["repo_id"] == "test/model"
        assert "start_time" in data

    def test_record_from_dict(self):
        """Test creating record from dictionary."""
        data = {
            "repo_id": "test/model",
            "files": ["file.gguf"],
            "total_size": 1024,
            "start_time": datetime.now().isoformat(),
            "status": "downloading",
        }
        record = DownloadRecord.from_dict(data)
        assert record.repo_id == "test/model"
        assert record.status == "downloading"


class TestDownloadHistoryInitialization:
    """Test suite for DownloadHistory initialization."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def history_file(self, temp_dir):
        """Create a temporary history file."""
        return temp_dir / "history.json"

    def test_initialization_creates_file(self, history_file):
        """Test that initialization creates history file."""
        history = DownloadHistory(history_file)
        assert history_file.exists()

    def test_initialization_with_existing_history(self, history_file):
        """Test initialization with existing history."""
        # Create existing history
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, "w") as f:
            import json

            json.dump([{"repo_id": "test/model"}], f)

        history = DownloadHistory(history_file)
        assert len(history._records) == 1

    def test_initialization_with_invalid_json(self, history_file):
        """Test initialization with invalid JSON."""
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, "w") as f:
            f.write("invalid json")

        history = DownloadHistory(history_file)
        assert len(history._records) == 0


class TestDownloadHistoryOperations:
    """Test suite for history operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def history_file(self, temp_dir):
        """Create a temporary history file."""
        return temp_dir / "history.json"

    @pytest.fixture
    def history(self, history_file):
        """Create a DownloadHistory instance."""
        return DownloadHistory(history_file)

    def test_start_download(self, history):
        """Test starting a download."""
        history.start_download("test/model", ["file.gguf"], 1024)
        assert len(history._records) == 1
        assert history._records[0].status == "downloading"
        assert history._records[0].repo_id == "test/model"

    def test_complete_download(self, history):
        """Test completing a download."""
        history.start_download("test/model", ["file.gguf"], 1024)
        history.complete_download("test/model", 1024)

        record = history._records[0]
        assert record.status == "completed"
        assert record.bytes_downloaded == 1024
        assert record.end_time is not None

    def test_fail_download(self, history):
        """Test failing a download."""
        history.start_download("test/model", ["file.gguf"], 1024)
        history.fail_download("test/model", 512, "Network error")

        record = history._records[0]
        assert record.status == "failed"
        assert record.bytes_downloaded == 512
        assert record.error_message == "Network error"

    def test_cancel_download(self, history):
        """Test cancelling a download."""
        history.start_download("test/model", ["file.gguf"], 1024)
        history.cancel_download("test/model", 512)

        record = history._records[0]
        assert record.status == "cancelled"
        assert record.bytes_downloaded == 512

    def test_get_records_by_repo_id(self, history):
        """Test filtering records by repo ID."""
        history.start_download("test/model1", ["file.gguf"], 1024)
        history.start_download("test/model2", ["file.gguf"], 1024)
        history.complete_download("test/model1", 1024)
        history.complete_download("test/model2", 1024)

        records = history.get_records(repo_id="test/model1")
        assert len(records) == 1
        assert records[0].repo_id == "test/model1"

    def test_get_records_by_status(self, history):
        """Test filtering records by status."""
        history.start_download("test/model1", ["file.gguf"], 1024)
        history.start_download("test/model2", ["file.gguf"], 1024)
        history.complete_download("test/model1", 1024)
        history.fail_download("test/model2", 512, "Error")

        completed_records = history.get_records(status="completed")
        failed_records = history.get_records(status="failed")

        assert len(completed_records) == 1
        assert len(failed_records) == 1
        assert completed_records[0].repo_id == "test/model1"
        assert failed_records[0].repo_id == "test/model2"

    def test_get_records_with_limit(self, history):
        """Test limiting number of records returned."""
        for i in range(5):
            history.start_download(f"test/model{i}", ["file.gguf"], 1024)

        records = history.get_records(limit=3)
        assert len(records) == 3


class TestDownloadHistoryStatistics:
    """Test suite for history statistics."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def history_file(self, temp_dir):
        """Create a temporary history file."""
        return temp_dir / "history.json"

    @pytest.fixture
    def history(self, history_file):
        """Create a DownloadHistory instance."""
        return DownloadHistory(history_file)

    def test_empty_statistics(self, history):
        """Test statistics with empty history."""
        stats = history.get_statistics()
        assert stats["total_downloads"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0
        assert stats["total_bytes"] == 0
        assert stats["success_rate"] == 0.0

    def test_statistics_with_downloads(self, history):
        """Test statistics with download records."""
        history.start_download("test/model1", ["file.gguf"], 1024)
        history.start_download("test/model2", ["file.gguf"], 1024)
        history.complete_download("test/model1", 1024)
        history.fail_download("test/model2", 512, "Error")

        stats = history.get_statistics()
        assert stats["total_downloads"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["total_bytes"] == 1024 + 512
        assert stats["success_rate"] == 50.0

    def test_clear_history(self, history):
        """Test clearing history."""
        history.start_download("test/model", ["file.gguf"], 1024)
        assert len(history._records) == 1

        history.clear_history()
        assert len(history._records) == 0

    def test_cleanup_old_records(self, history):
        """Test cleaning up old records."""
        from datetime import timedelta

        old_time = datetime.now() - timedelta(days=31)
        recent_time = datetime.now() - timedelta(days=1)

        # Add record with old time
        old_record = DownloadRecord(
            repo_id="old/model",
            files=["file.gguf"],
            total_size=1024,
            start_time=old_time,
        )
        history._records.append(old_record)

        # Add record with recent time
        history.start_download("recent/model", ["file.gguf"], 1024)
        history.complete_download("recent/model", 1024)

        removed = history.cleanup_old_records(days=30)
        assert removed == 1
        assert len(history._records) == 1
        assert history._records[0].repo_id == "recent/model"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
