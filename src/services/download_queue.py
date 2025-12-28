"""Download queue management with priority support."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, List, Optional

from src.exceptions import DownloadError

logger = logging.getLogger(__name__)


class DownloadPriority(IntEnum):
    """Priority levels for downloads."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass(order=True)
class DownloadTask:
    """
    A download task in the queue.

    Ordered by priority, then by creation time (earlier first).
    """

    repo_id: str
    files: List[str]
    priority: DownloadPriority = DownloadPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    callback: Optional[callable] = None
    progress_data: Optional[dict] = field(default=None, compare=False)

    def __post_init__(self):
        """Validate download task after creation."""
        if not self.repo_id:
            raise ValueError("repo_id is required")
        if not self.files:
            raise ValueError("files list cannot be empty")
        if "/" not in self.repo_id:
            raise ValueError(f"Invalid repo_id format: {self.repo_id}")


class DownloadQueueManager:
    """
    Manages a priority queue of download tasks.

    Supports concurrent downloads with priority-based ordering.
    """

    def __init__(self, max_concurrent_downloads: int = 1):
        """
        Initialize download queue manager.

        Args:
            max_concurrent_downloads: Maximum number of concurrent downloads
        """
        self.max_concurrent = max_concurrent_downloads
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._active_downloads: set = set()
        self._shutdown = False
        self._worker_task: Optional[asyncio.Task] = None
        self._download_callback: Optional[callable] = None
        logger.info(
            f"DownloadQueueManager initialized with max_concurrent={max_concurrent_downloads}"
        )

    def set_download_callback(self, callback: Any) -> None:
        """
        Set the callback function to execute downloads.

        Args:
            callback: Async function that accepts (repo_id, files, progress_callback)
        """
        self._download_callback = callback

    async def start(self) -> None:
        """Start the queue worker."""
        if self._worker_task is not None:
            logger.warning("Queue worker already running")
            return

        self._worker_task = asyncio.create_task(self._worker())
        logger.info("Download queue worker started")

    async def stop(self) -> None:
        """Stop the queue worker gracefully."""
        if self._worker_task is None:
            return

        logger.info("Stopping download queue worker...")
        self._shutdown = True

        # Cancel worker task
        if not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        # Wait for active downloads to complete (with timeout)
        if self._active_downloads:
            logger.info(f"Waiting for {len(self._active_downloads)} active downloads...")
            try:
                await asyncio.wait_for(self._wait_for_active_downloads(), timeout=30)
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for active downloads")

        self._worker_task = None
        self._shutdown = False
        logger.info("Download queue worker stopped")

    async def _wait_for_active_downloads(self) -> None:
        """Wait for all active downloads to complete."""
        while self._active_downloads and not self._shutdown:
            await asyncio.sleep(0.1)

    async def _worker(self) -> None:
        """Queue worker that processes download tasks."""
        while not self._shutdown:
            try:
                # Get next task with timeout to allow checking shutdown
                task: DownloadTask = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                if self._download_callback is None:
                    logger.error("No download callback set")
                    self._queue.task_done()
                    continue

                # Wait for available slot
                while len(self._active_downloads) >= self.max_concurrent:
                    if self._shutdown:
                        self._queue.task_done()
                        return
                    await asyncio.sleep(0.1)

                # Start download
                download_key = (task.repo_id, tuple(task.files))
                self._active_downloads.add(download_key)
                self._queue.task_done()

                logger.info(
                    f"Starting download: {task.repo_id} "
                    f"(priority={task.priority.name}, "
                    f"active={len(self._active_downloads)}/{self.max_concurrent})"
                )

                # Execute download in background
                asyncio.create_task(self._execute_download(task, download_key))

            except asyncio.TimeoutError:
                # Timeout is expected, just loop and check shutdown
                continue
            except asyncio.CancelledError:
                logger.info("Queue worker cancelled")
                break

        logger.info("Queue worker exiting")

    async def _execute_download(self, task: DownloadTask, download_key: tuple) -> None:
        """
        Execute a download task.

        Args:
            task: Download task to execute
            download_key: Unique key for this download
        """
        try:
            if self._download_callback:
                await self._download_callback(
                    task.repo_id,
                    task.files,
                    task.callback,
                )
            logger.info(f"Completed download: {task.repo_id}")
        except DownloadError as e:  # noqa: F841 - e is used in f-string
            logger.error(f"Download failed: {task.repo_id} - {e}")
        except Exception as e:  # noqa: F841 - e is used in f-string
            logger.error(f"Unexpected error in download: {task.repo_id}", exc_info=True)
        finally:
            # Remove from active downloads
            if download_key in self._active_downloads:
                self._active_downloads.remove(download_key)

    def add(
        self,
        repo_id: str,
        files: List[str],
        priority: DownloadPriority = DownloadPriority.NORMAL,
        callback: Optional[callable] = None,
    ) -> None:
        """
        Add a download task to the queue.

        Args:
            repo_id: Repository ID to download
            files: List of files to download
            priority: Download priority (default: NORMAL)
            callback: Optional progress callback

        Raises:
            ValueError: If repo_id or files are invalid
        """
        if self._shutdown:
            logger.warning("Cannot add task: queue is shutting down")
            return

        try:
            task = DownloadTask(repo_id=repo_id, files=files, priority=priority, callback=callback)
        except ValueError as e:
            logger.error(f"Invalid download task: {e}")
            return

        # Sort order: higher priority first, then earlier creation time
        # PriorityQueue uses min-heap, so we negate priority
        priority_value = (-task.priority.value, task.created_at.timestamp())
        self._queue.put_nowait((priority_value, task))

        logger.info(
            f"Added download task: {repo_id} "
            f"(priority={priority.name}, queue_size={self._queue.qsize()})"
        )

    async def get_next(self) -> Optional[DownloadTask]:
        """
        Get the next download task without removing it from queue.

        Args:
            Next download task or None if queue is empty

        Returns:
            DownloadTask or None
        """
        if self._queue.empty():
            return None

        priority_value, task = await self._queue.get()
        self._queue.task_done()
        return task

    def get_queue_size(self) -> int:
        """
        Get the number of tasks in the queue.

        Returns:
            Queue size (excluding active downloads)
        """
        return self._queue.qsize()

    def get_active_count(self) -> int:
        """
        Get the number of active downloads.

        Returns:
            Number of currently downloading tasks
        """
        return len(self._active_downloads)

    def clear_queue(self) -> None:
        """Clear all pending tasks from the queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
        logger.info(f"Cleared {self._queue.qsize()} pending tasks from queue")

    def get_status(self) -> dict:
        """
        Get queue status information.

        Returns:
            Dictionary with queue status
        """
        return {
            "queue_size": self.get_queue_size(),
            "active_downloads": self.get_active_count(),
            "max_concurrent": self.max_concurrent,
            "is_running": self._worker_task is not None and not self._worker_task.done(),
        }
