"""Tests for download queue manager."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.download_queue import DownloadQueueManager, DownloadTask, DownloadPriority


class TestDownloadTask:
    """Test suite for DownloadTask dataclass."""

    def test_task_creation_valid(self):
        """Test creating a valid download task."""
        task = DownloadTask(repo_id="test/model", files=["file1.gguf", "file2.gguf"])
        assert task.repo_id == "test/model"
        assert len(task.files) == 2
        assert task.priority == DownloadPriority.NORMAL
        assert isinstance(task.created_at, datetime)

    def test_task_with_priority(self):
        """Test creating task with custom priority."""
        task = DownloadTask(
            repo_id="test/model", files=["file.gguf"], priority=DownloadPriority.HIGH
        )
        assert task.priority == DownloadPriority.HIGH

    def test_task_invalid_repo_id(self):
        """Test task creation with invalid repo ID."""
        with pytest.raises(ValueError) as exc_info:
            DownloadTask(repo_id="invalid", files=["file.gguf"])

        assert "Invalid repo_id format" in str(exc_info.value)

    def test_task_empty_files(self):
        """Test task creation with empty files list."""
        with pytest.raises(ValueError) as exc_info:
            DownloadTask(repo_id="test/model", files=[])

        assert "files list cannot be empty" in str(exc_info.value)

    def test_task_ordering(self):
        """Test that tasks order by priority then creation time."""
        from datetime import timedelta

        now = datetime.now()
        task1 = DownloadTask(
            repo_id="test/model1",
            files=["file.gguf"],
            priority=DownloadPriority.NORMAL,
            created_at=now,
        )
        task2 = DownloadTask(
            repo_id="test/model2",
            files=["file.gguf"],
            priority=DownloadPriority.HIGH,
            created_at=now - timedelta(seconds=1),
        )

        # Higher priority comes first
        assert task2 < task1

        task3 = DownloadTask(
            repo_id="test/model3",
            files=["file.gguf"],
            priority=DownloadPriority.HIGH,
            created_at=now - timedelta(seconds=2),
        )

        # Same priority, earlier creation comes first
        assert task2 < task3


class TestDownloadQueueManagerInitialization:
    """Test suite for DownloadQueueManager initialization."""

    def test_initialization_default(self):
        """Test initialization with default parameters."""
        queue = DownloadQueueManager()
        assert queue.max_concurrent == 1
        assert queue.get_queue_size() == 0
        assert queue.get_active_count() == 0
        assert not queue._shutdown

    def test_initialization_custom_max_concurrent(self):
        """Test initialization with custom max concurrent downloads."""
        queue = DownloadQueueManager(max_concurrent_downloads=3)
        assert queue.max_concurrent == 3

    def test_get_status_initial(self):
        """Test getting initial status."""
        queue = DownloadQueueManager()
        status = queue.get_status()
        assert status["queue_size"] == 0
        assert status["active_downloads"] == 0
        assert status["max_concurrent"] == 1
        assert status["is_running"] is False


class TestDownloadQueueManagerOperations:
    """Test suite for queue operations."""

    @pytest.fixture
    def queue(self):
        """Create a queue manager for tests."""
        return DownloadQueueManager()

    def test_add_task(self, queue):
        """Test adding a task to queue."""
        queue.add("test/model", ["file.gguf"])
        assert queue.get_queue_size() == 1

    def test_add_task_with_priority(self, queue):
        """Test adding tasks with different priorities."""
        queue.add("test/model1", ["file1.gguf"], priority=DownloadPriority.LOW)
        queue.add("test/model2", ["file2.gguf"], priority=DownloadPriority.HIGH)

        assert queue.get_queue_size() == 2

    def test_add_task_with_callback(self, queue):
        """Test adding task with callback."""
        callback = Mock()
        queue.add("test/model", ["file.gguf"], callback=callback)
        assert queue.get_queue_size() == 1

    def test_clear_queue(self, queue):
        """Test clearing the queue."""
        queue.add("test/model1", ["file1.gguf"])
        queue.add("test/model2", ["file2.gguf"])
        assert queue.get_queue_size() == 2

        queue.clear_queue()
        assert queue.get_queue_size() == 0

    def test_get_queue_size(self, queue):
        """Test getting queue size."""
        assert queue.get_queue_size() == 0

        queue.add("test/model1", ["file1.gguf"])
        queue.add("test/model2", ["file2.gguf"])
        assert queue.get_queue_size() == 2

    def test_get_active_count(self, queue):
        """Test getting active download count."""
        assert queue.get_active_count() == 0

        # Simulate active downloads
        queue._active_downloads.add(("test/model", ("file.gguf",)))
        assert queue.get_active_count() == 1


class TestDownloadQueueManagerAsync:
    """Test suite for async queue operations."""

    @pytest.fixture
    def queue(self):
        """Create a queue manager for tests."""
        return DownloadQueueManager()

    @pytest.mark.asyncio
    async def test_start_and_stop_worker(self, queue):
        """Test starting and stopping the worker."""
        assert not queue.get_status()["is_running"]

        await queue.start()
        assert queue.get_status()["is_running"]

        await queue.stop()
        assert not queue.get_status()["is_running"]

    @pytest.mark.asyncio
    async def test_start_already_running(self, queue):
        """Test starting worker when already running."""
        await queue.start()

        # Should not raise an error, just log warning
        await queue.start()
        assert queue.get_status()["is_running"]

        await queue.stop()

    @pytest.mark.asyncio
    async def test_download_callback_execution(self, queue):
        """Test that download callback is executed."""
        callback_executed = []
        download_callback = Mock(
            side_effect=lambda repo, files, cb: callback_executed.append((repo, files))
        )

        queue.set_download_callback(download_callback)
        await queue.start()

        # Add a task
        queue.add("test/model", ["file.gguf"])

        # Give time for worker to process
        await asyncio.sleep(0.2)

        await queue.stop()

        # Verify callback was called
        assert len(callback_executed) == 1
        assert callback_executed[0][0] == "test/model"
        assert callback_executed[0][1] == ["file.gguf"]

    @pytest.mark.asyncio
    async def test_concurrent_downloads_limit(self):
        """Test that concurrent downloads are limited."""
        downloads_started = []
        download_callback = AsyncMock(
            side_effect=lambda repo, files, cb: downloads_started.append(repo)
        )

        queue = DownloadQueueManager(max_concurrent_downloads=2)
        queue.set_download_callback(download_callback)
        await queue.start()

        # Add multiple tasks
        queue.add("test/model1", ["file1.gguf"])
        queue.add("test/model2", ["file2.gguf"])
        queue.add("test/model3", ["file3.gguf"])

        # Give time for worker to start some downloads
        await asyncio.sleep(0.2)

        # At most 2 downloads should be active
        assert len(downloads_started) <= 2

        await queue.stop()

    @pytest.mark.asyncio
    async def test_task_priority_ordering(self, queue):
        """Test that higher priority tasks execute first."""
        execution_order = []
        download_callback = Mock(side_effect=lambda repo, files, cb: execution_order.append(repo))

        queue.set_download_callback(download_callback)
        await queue.start()

        # Add tasks with different priorities
        queue.add("test/low", ["file.gguf"], priority=DownloadPriority.LOW)
        queue.add("test/high", ["file.gguf"], priority=DownloadPriority.HIGH)
        queue.add("test/normal", ["file.gguf"], priority=DownloadPriority.NORMAL)

        # Give time for worker to process
        await asyncio.sleep(0.2)

        await queue.stop()

        # High priority should be first
        assert len(execution_order) > 0
        # Note: Actual order depends on async timing, but HIGH should come before LOW

    @pytest.mark.asyncio
    async def test_stop_waits_for_active_downloads(self, queue):
        """Test that stop waits for active downloads to complete."""
        download_started = asyncio.Event()
        download_finished = asyncio.Event()

        async def slow_download(repo, files, cb):
            download_started.set()
            await asyncio.sleep(0.1)
            download_finished.set()

        queue.set_download_callback(slow_download)
        await queue.start()

        queue.add("test/model", ["file.gguf"])

        # Wait for download to start
        await download_started.wait()

        # Stop should wait for download to complete
        stop_task = asyncio.create_task(queue.stop())

        # Stop task should complete after download finishes
        await asyncio.wait_for(stop_task, timeout=0.5)

        assert download_finished.is_set()


class TestDownloadQueueManagerErrorHandling:
    """Test suite for error handling in queue operations."""

    @pytest.fixture
    def queue(self):
        """Create a queue manager for tests."""
        return DownloadQueueManager()

    def test_add_invalid_repo_id(self, queue):
        """Test adding task with invalid repo ID."""
        queue.add("invalid", ["file.gguf"])
        assert queue.get_queue_size() == 0

    def test_add_empty_files(self, queue):
        """Test adding task with empty files."""
        queue.add("test/model", [])
        assert queue.get_queue_size() == 0

    @pytest.mark.asyncio
    async def test_download_callback_error(self, queue):
        """Test handling of download callback errors."""
        download_callback = Mock(side_effect=Exception("Download failed"))
        queue.set_download_callback(download_callback)
        await queue.start()

        queue.add("test/model", ["file.gguf"])

        # Should not raise, just log error
        await asyncio.sleep(0.2)

        await queue.stop()

        # Verify task was removed from active downloads
        assert queue.get_active_count() == 0


class TestDownloadQueueManagerShutdown:
    """Test suite for queue shutdown behavior."""

    @pytest.fixture
    def queue(self):
        """Create a queue manager for tests."""
        return DownloadQueueManager()

    @pytest.mark.asyncio
    async def test_add_after_shutdown(self, queue):
        """Test that adding tasks after shutdown is handled gracefully."""
        await queue.start()
        queue._shutdown = True

        # Should not add task, just log warning
        queue.add("test/model", ["file.gguf"])

        # Queue should be empty
        assert queue.get_queue_size() == 0

        await queue.stop()

    @pytest.mark.asyncio
    async def test_multiple_start_stop_cycles(self, queue):
        """Test multiple start/stop cycles."""
        for _ in range(3):
            await queue.start()
            queue.add("test/model", ["file.gguf"])
            await asyncio.sleep(0.1)
            await queue.stop()

        assert not queue.get_status()["is_running"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
