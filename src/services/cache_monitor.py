"""Cache monitoring for HuggingFace Hub download progress."""

import logging
import time
from pathlib import Path
from typing import Optional, List, Tuple

from huggingface_hub.constants import HUGGINGFACE_HUB_CACHE

logger = logging.getLogger(__name__)


class CacheMonitor:
    """
    Monitors HuggingFace Hub cache directories during download.

    Tracks file growth in both local and global cache directories
    to provide accurate progress updates during downloads.
    """

    def __init__(self, local_dir: Path, filename: str):
        """
        Initialize cache monitor.

        Args:
            local_dir: Directory where file is being downloaded to
            filename: Name of the file being downloaded
        """
        self.local_dir = local_dir
        self.filename = filename
        self.target_file = local_dir / filename

        # Cache directory paths
        self.local_cache_dir = local_dir / ".cache" / "huggingface"
        self.local_cache_download = self.local_cache_dir / "download"
        self.global_cache_dir = Path(HUGGINGFACE_HUB_CACHE)
        self.global_cache_download = self.global_cache_dir / "download"

        # Monitoring state
        self._initial_incomplete_size = 0
        self._last_reported_size = 0
        self._last_update = time.time()
        self._monitoring_found_file = False

    def get_initial_incomplete_size(self) -> int:
        """
        Get the initial size of incomplete file at download start.

        This is used to avoid double-counting bytes when resuming downloads.

        Returns:
            Initial size in bytes (0 if no incomplete file found)
        """
        # Collect candidates from all potential locations
        candidates = self._collect_all_candidates()

        # Use most recently modified file's size as initial
        if candidates:
            candidates.sort(reverse=True)  # Most recent first
            self._initial_incomplete_size = candidates[0][1]
            logger.info(
                f"Initial incomplete file size: {self._initial_incomplete_size:,} bytes "
                f"(resuming download)"
            )

        return self._initial_incomplete_size

    def get_current_size(self) -> Tuple[int, Optional[str]]:
        """
        Get current size of the file being downloaded.

        Searches in multiple cache locations and returns the size
        from the most recently modified file.

        Returns:
            Tuple of (current_size_bytes, location_description)
        """
        # Collect all candidates and pick most recently modified
        candidates = self._collect_candidates_for_monitoring()

        # Use most recently modified source
        if candidates:
            candidates.sort(reverse=True)  # Most recent first
            current_size = candidates[0][1]
            found_location = candidates[0][2]

            # Log that we found a file (only once)
            if not self._monitoring_found_file and found_location != "target_file":
                self._monitoring_found_file = True
                logger.info(f"Monitoring file in: {found_location}")

            return current_size, found_location

        return 0, None

    def should_send_progress(self, current_size: int) -> bool:
        """
        Determine if progress update should be sent.

        Progress is sent when:
        1. File size has actually increased (not stale)
        2. Heartbeat interval elapsed (even if size unchanged)

        Args:
            current_size: Current file size in bytes

        Returns:
            True if progress should be sent, False otherwise
        """
        now = time.time()
        size_changed = current_size > self._last_reported_size
        time_since_update = now - self._last_update

        # Send progress when size increases
        if size_changed:
            return True

        # Heartbeat - send progress even when size doesn't change
        # This prevents UI from appearing frozen during slow periods
        if time_since_update >= 0.5:
            return True

        return False

    def update_tracking(self, current_size: int):
        """
        Update internal tracking state after progress is sent.

        Args:
            current_size: Current file size in bytes
        """
        self._last_reported_size = current_size
        self._last_update = time.time()

    def log_monitoring_status(self) -> Optional[str]:
        """
        Log periodic monitoring status.

        Returns warning message if file not found, None otherwise.

        Returns:
            Warning message or None
        """
        now = time.time()
        time_since_update = now - self._last_update

        # Log warning if still searching for file
        if time_since_update >= 2.0 and not self._monitoring_found_file:
            self._last_update = now  # Reset to avoid spam
            return (
                f"Still searching for download file. Checked: "
                f"local_cache={self.local_cache_download.exists()}, "
                f"global_cache={self.global_cache_download.exists()}, "
                f"target={self.target_file.exists()}"
            )

        return None

    def _collect_all_candidates(self) -> List[Tuple[float, int]]:
        """
        Collect all candidate files from all cache locations.

        Returns:
            List of (modification_time, size) tuples
        """
        candidates = []

        # Priority 1: Final file exists
        if self.target_file.exists():
            candidates.append((self.target_file.stat().st_mtime, self.target_file.stat().st_size))

        # Priority 2: Local cache incomplete files
        if self.local_cache_download.exists():
            for f in self.local_cache_download.glob("*.incomplete"):
                candidates.append((f.stat().st_mtime, f.stat().st_size))
                logger.info(f"Found local cache incomplete: {f.name} ({f.stat().st_size} bytes)")

        # Priority 3: Global cache incomplete files
        if self.global_cache_download.exists():
            for f in self.global_cache_download.glob("*.incomplete"):
                candidates.append((f.stat().st_mtime, f.stat().st_size))
                logger.info(f"Found global cache incomplete: {f.name} ({f.stat().st_size} bytes)")

        return candidates

    def _collect_candidates_for_monitoring(self) -> List[Tuple[float, int, str]]:
        """
        Collect candidate files during active monitoring.

        Returns:
            List of (modification_time, size, location) tuples
        """
        candidates = []

        # Priority 1: Check if final file exists and is growing
        if self.target_file.exists():
            candidates.append(
                (
                    self.target_file.stat().st_mtime,
                    self.target_file.stat().st_size,
                    "target_file",
                )
            )

        # Priority 2: Check LOCAL cache for incomplete files
        if self.local_cache_download.exists():
            incomplete_files = list(self.local_cache_download.glob("*.incomplete"))
            for f in incomplete_files:
                candidates.append((f.stat().st_mtime, f.stat().st_size, f"local_cache ({f.name})"))

        # Priority 3: Check GLOBAL cache as fallback
        if self.global_cache_download.exists():
            incomplete_files = list(self.global_cache_download.glob("*.incomplete"))
            for f in incomplete_files:
                candidates.append((f.stat().st_mtime, f.stat().st_size, f"global_cache ({f.name})"))

        return candidates
