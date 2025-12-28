"""Download history tracking with statistics."""

import json
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict

from src.exceptions import StorageError

logger = logging.getLogger(__name__)


@dataclass
class DownloadRecord:
    """A record of a download."""

    repo_id: str
    files: List[str]
    total_size: int
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "pending"  # pending, downloading, completed, failed, cancelled
    error_message: Optional[str] = None
    download_speed: Optional[float] = None  # bytes per second
    bytes_downloaded: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result["start_time"] = self.start_time.isoformat()
        if self.end_time:
            result["end_time"] = self.end_time.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadRecord":
        """Create DownloadRecord from dictionary."""
        data = data.copy()
        if isinstance(data.get("start_time"), str):
            data["start_time"] = datetime.fromisoformat(data["start_time"])
        if isinstance(data.get("end_time"), str):
            data["end_time"] = datetime.fromisoformat(data["end_time"])

        # Provide defaults for missing fields
        data.setdefault("repo_id", "")
        data.setdefault("files", [])
        data.setdefault("total_size", 0)
        data.setdefault("start_time", datetime.now())
        data.setdefault("status", "pending")
        data.setdefault("end_time", None)
        data.setdefault("error_message", None)
        data.setdefault("download_speed", None)
        data.setdefault("bytes_downloaded", 0)

        return cls(**data)


class DownloadHistory:
    """
    Manages download history and statistics.

    Tracks all download attempts with timing, status, and statistics.
    """

    def __init__(self, history_file: Path):
        """
        Initialize download history manager.

        Args:
            history_file: Path to JSON file storing history
        """
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._records: List[DownloadRecord] = []
        self._load_history()

        # Create history file if it doesn't exist
        if not self.history_file.exists():
            self._save_history()

        logger.info(f"DownloadHistory initialized with {len(self._records)} records")

    def _load_history(self) -> None:
        """Load history from file."""
        if not self.history_file.exists():
            logger.info("No history file found, starting fresh")
            self._records = []
            return

        try:
            with open(self.history_file, "r") as f:
                data = json.load(f)
                self._records = [DownloadRecord.from_dict(r) for r in data]
            logger.info(f"Loaded {len(self._records)} download records")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load history: {e}", exc_info=True)
            self._records = []
        finally:
            # Ensure records list is initialized
            if not hasattr(self, "_records"):
                self._records = []

    def _save_history(self) -> None:
        """Save history to file."""
        try:
            data = [r.to_dict() for r in self._records]
            with open(self.history_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self._records)} download records")
        except IOError as e:
            raise StorageError(f"Failed to save history: {e}") from e

    def start_download(self, repo_id: str, files: List[str], total_size: int) -> None:
        """
        Start tracking a new download.

        Args:
            repo_id: Repository ID being downloaded
            files: List of files being downloaded
            total_size: Total size in bytes
        """
        record = DownloadRecord(
            repo_id=repo_id,
            files=files,
            total_size=total_size,
            start_time=datetime.now(),
            status="downloading",
        )
        self._records.append(record)
        self._save_history()
        logger.info(f"Started tracking download: {repo_id}")

    def update_download(
        self,
        repo_id: str,
        status: Optional[str] = None,
        bytes_downloaded: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Update an ongoing download record.

        Args:
            repo_id: Repository ID to update
            status: New status (downloading, completed, failed, cancelled)
            bytes_downloaded: Number of bytes downloaded so far
            error_message: Error message if download failed
        """
        record = self._get_latest_record(repo_id)
        if record is None:
            logger.warning(f"No record found for {repo_id}, skipping update")
            return

        if status is not None:
            record.status = status
            if status in ["completed", "failed", "cancelled"]:
                record.end_time = datetime.now()
        if bytes_downloaded is not None:
            record.bytes_downloaded = bytes_downloaded
            # Calculate average speed
            elapsed_seconds = (
                (record.end_time or datetime.now()) - record.start_time
            ).total_seconds()
            if elapsed_seconds > 0:
                record.download_speed = bytes_downloaded / elapsed_seconds
        if error_message is not None:
            record.error_message = error_message

        self._save_history()
        logger.debug(f"Updated download record: {repo_id} - status={status}")

    def complete_download(self, repo_id: str, bytes_downloaded: int) -> None:
        """
        Mark a download as completed.

        Args:
            repo_id: Repository ID that completed
            bytes_downloaded: Total bytes downloaded
        """
        self.update_download(repo_id, status="completed", bytes_downloaded=bytes_downloaded)
        logger.info(f"Marked download as completed: {repo_id}")

    def fail_download(self, repo_id: str, bytes_downloaded: int, error_message: str) -> None:
        """
        Mark a download as failed.

        Args:
            repo_id: Repository ID that failed
            bytes_downloaded: Bytes downloaded before failure
            error_message: Error message
        """
        self.update_download(
            repo_id, status="failed", bytes_downloaded=bytes_downloaded, error_message=error_message
        )
        logger.error(f"Marked download as failed: {repo_id} - {error_message}")

    def cancel_download(self, repo_id: str, bytes_downloaded: int) -> None:
        """
        Mark a download as cancelled.

        Args:
            repo_id: Repository ID that was cancelled
            bytes_downloaded: Bytes downloaded before cancellation
        """
        self.update_download(repo_id, status="cancelled", bytes_downloaded=bytes_downloaded)
        logger.info(f"Marked download as cancelled: {repo_id}")

    def _get_latest_record(self, repo_id: str) -> Optional[DownloadRecord]:
        """
        Get the most recent record for a repository.

        Args:
            repo_id: Repository ID to search for

        Returns:
            Latest DownloadRecord or None
        """
        for record in reversed(self._records):
            if record.repo_id == repo_id:
                return record
        return None

    def get_records(
        self,
        repo_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[DownloadRecord]:
        """
        Get download records with optional filtering.

        Args:
            repo_id: Filter by repository ID (optional)
            status: Filter by status (optional)
            limit: Maximum number of records to return (optional)

        Returns:
            List of DownloadRecord
        """
        records = self._records

        if repo_id is not None:
            records = [r for r in records if r.repo_id == repo_id]
        if status is not None:
            records = [r for r in records if r.status == status]

        # Sort by start time (most recent first)
        records = sorted(records, key=lambda r: r.start_time, reverse=True)

        if limit is not None:
            records = records[:limit]

        return records

    def get_statistics(self) -> Dict[str, any]:
        """
        Get download statistics.

        Returns:
            Dictionary with statistics
        """
        if not self._records:
            return {
                "total_downloads": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
                "total_bytes": 0,
                "success_rate": 0.0,
                "average_speed": 0.0,
            }

        completed = [r for r in self._records if r.status == "completed"]
        failed = [r for r in self._records if r.status == "failed"]
        cancelled_records = [r for r in self._records if r.status == "cancelled"]

        total_bytes = sum(r.bytes_downloaded for r in self._records)
        average_speed = (
            sum(r.download_speed or 0 for r in completed) / len(completed) if completed else 0.0
        )

        return {
            "total_downloads": len(self._records),
            "completed": len(completed),
            "failed": len(failed),
            "cancelled": len(cancelled_records),
            "total_bytes": total_bytes,
            "success_rate": len(completed) / len(self._records) * 100 if self._records else 0.0,
            "average_speed": average_speed,
        }

    def clear_history(self) -> None:
        """Clear all download records."""
        self._records = []
        self._save_history()
        logger.info("Download history cleared")

    def cleanup_old_records(self, days: int = 30) -> int:
        """
        Remove records older than specified days.

        Args:
            days: Number of days to keep records

        Returns:
            Number of records removed
        """
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        original_count = len(self._records)
        self._records = [r for r in self._records if r.start_time.timestamp() > cutoff_time]
        removed_count = original_count - len(self._records)

        if removed_count > 0:
            self._save_history()
            logger.info(f"Removed {removed_count} old download records")

        return removed_count
