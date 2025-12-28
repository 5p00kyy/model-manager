"""Download manager with byte-level progress monitoring."""

import asyncio
import hashlib
import logging
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from huggingface_hub import hf_hub_download

from src.services.cache_monitor import CacheMonitor
from src.utils.helpers import ProgressCallback, ProgressData, DownloadSpeedCalculator, calculate_eta
from src.exceptions import DownloadError, HuggingFaceError

logger = logging.getLogger(__name__)

# Progress monitoring constants
PROGRESS_HEARTBEAT_INTERVAL = 0.5  # seconds - send progress updates even when stalled
PROGRESS_POLL_INTERVAL = 0.1  # seconds - how often to check file size
SPEED_CALC_WINDOW_SIZE = 10  # samples - moving window for speed calculation


class DownloadManager:
    """Download manager with byte-level progress tracking."""

    def __init__(self, hf_client, storage_manager):
        """Initialize download manager."""
        self.hf_client = hf_client
        self.storage = storage_manager
        self._cancelled = False
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._speed_calculator = None
        self._is_resuming = False
        self._initial_bytes_before = 0
        self._shutdown = False

    def shutdown(self) -> None:
        """Shutdown the executor gracefully."""
        if not self._shutdown:
            self._shutdown = True
            self._cancelled = True
            self._executor.shutdown(wait=False, cancel_futures=True)
            logger.info("DownloadManager executor shutdown")

    def __del__(self):
        """Cleanup executor on deletion."""
        self.shutdown()

    async def download_model(
        self, repo_id: str, files: List[str], progress_callback: Optional[ProgressCallback] = None
    ) -> bool:
        """Download model files with per-file progress tracking."""
        self._cancelled = False
        local_dir = self.storage.get_model_path(repo_id)
        local_dir.mkdir(parents=True, exist_ok=True)

        # Get file sizes
        logger.info(f"Fetching file sizes for {repo_id}")
        file_sizes = self.hf_client.get_file_sizes(repo_id)
        total_size = sum(file_sizes.get(f, 0) for f in files)

        logger.info(
            f"Starting download: repo={repo_id}, files={len(files)}, "
            f"total_size={total_size:,} bytes"
        )

        overall_downloaded = 0
        start_time = time.time()

        # Initialize speed calculator for accurate real-time speed tracking
        self._speed_calculator = DownloadSpeedCalculator(window_size=SPEED_CALC_WINDOW_SIZE)

        # Calculate initial bytes already downloaded (for resumed downloads)
        self._initial_bytes_before = 0
        for filename in files:
            file_path = local_dir / filename
            if file_path.exists():
                self._initial_bytes_before += file_path.stat().st_size

        # Seed speed calculator with initial bytes to avoid erratic speeds
        self._is_resuming = self._initial_bytes_before > 0
        if self._is_resuming:
            logger.info(
                f"Download resuming with {self._initial_bytes_before:,} bytes already downloaded"
            )
            self._speed_calculator.update(self._initial_bytes_before)

        try:
            for idx, filename in enumerate(files):
                if self._cancelled:
                    logger.info("Download cancelled by user")
                    return False

                file_size = file_sizes.get(filename, 0)
                file_path = local_dir / filename

                # Check if file already exists
                if file_path.exists():
                    existing_size = file_path.stat().st_size
                    if existing_size == file_size and file_size > 0:
                        logger.info(f"File {filename} already exists, skipping")
                        overall_downloaded += file_size

                        # Send progress update
                        if progress_callback:
                            self._send_progress(
                                progress_callback,
                                repo_id,
                                filename,
                                idx + 1,
                                len(files),
                                file_size,
                                file_size,
                                overall_downloaded,
                                total_size,
                                start_time,
                            )
                        continue

                logger.info(f"Downloading file {idx + 1}/{len(files)}: {filename}")

                # Send "starting" progress
                if progress_callback:
                    self._send_progress(
                        progress_callback,
                        repo_id,
                        filename,
                        idx + 1,
                        len(files),
                        0,
                        file_size,
                        overall_downloaded,
                        total_size,
                        start_time,
                    )

                # Retry logic for transient failures
                max_retries = 3
                retry_count = 0
                success = False

                while retry_count < max_retries and not success:
                    try:
                        # Download file with byte-level progress monitoring
                        await self._download_with_progress(
                            repo_id=repo_id,
                            filename=filename,
                            local_dir=local_dir,
                            file_size=file_size,
                            file_idx=idx,
                            total_files=len(files),
                            overall_downloaded_before=overall_downloaded,
                            total_size=total_size,
                            start_time=start_time,
                            progress_callback=progress_callback,
                        )

                        # Update overall progress
                        overall_downloaded += file_size
                        success = True

                        logger.info(f"Completed download of {filename}")

                        # Verify checksum if available
                        self._verify_checksum(file_path, None)

                    except asyncio.CancelledError:
                        logger.info(f"Download of {filename} cancelled")
                        raise
                    except HuggingFaceError as e:
                        # Handle HuggingFace API errors - don't retry these
                        logger.error(
                            f"HuggingFace API error downloading {filename}: {e}", exc_info=True
                        )
                        raise DownloadError(f"HuggingFace error: {e}") from e
                    except OSError as e:
                        # Handle file system, I/O, and network errors
                        # (includes ConnectionError, TimeoutError)
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.warning(
                                f"Error downloading {filename} (attempt "
                                f"{retry_count}/{max_retries}): {e}. Retrying...",
                                exc_info=True,
                            )
                            await asyncio.sleep(2**retry_count)
                        else:
                            logger.error(
                                f"Failed to download {filename} "
                                f"after {max_retries} attempts: {e}",
                                exc_info=True,
                            )
                            raise DownloadError(f"Failed to download {filename}: {e}") from e

            # Get commit SHA and save metadata
            logger.info(f"Fetching commit SHA for {repo_id}")
            commit_sha = self.hf_client.get_commit_sha(repo_id)
            self.storage.save_model_metadata(repo_id, commit_sha)

            # Final progress
            if progress_callback:
                progress_data: ProgressData = {
                    "repo_id": repo_id,
                    "current_file": files[-1] if files else "",
                    "current_file_index": len(files),
                    "total_files": len(files),
                    "current_file_downloaded": file_sizes.get(files[-1], 0) if files else 0,
                    "current_file_total": file_sizes.get(files[-1], 0) if files else 0,
                    "overall_downloaded": total_size,
                    "overall_total": total_size,
                    "speed": 0,
                    "eta": 0,
                    "completed": True,
                }
                progress_callback(progress_data)

            elapsed = time.time() - start_time
            logger.info(f"Download completed: {repo_id} in {elapsed:.2f}s")
            return True

        except asyncio.CancelledError:
            logger.info("Download cancelled")
            return False
        except DownloadError:
            # Re-raise DownloadError as-is
            raise
        except HuggingFaceError as e:
            logger.error(f"HuggingFace API error: {e}", exc_info=True)
            raise DownloadError(f"HuggingFace error: {e}") from e
        except OSError as e:
            # Handle file system, I/O, and network errors
            logger.error(f"System error during download: {e}", exc_info=True)
            raise DownloadError(f"System error: {e}") from e

    async def _download_with_progress(
        self,
        repo_id: str,
        filename: str,
        local_dir: Path,
        file_size: int,
        file_idx: int,
        total_files: int,
        overall_downloaded_before: int,
        total_size: int,
        start_time: float,
        progress_callback: Optional[ProgressCallback],
    ):
        """Download a file with byte-level progress monitoring."""
        loop = asyncio.get_event_loop()

        # Start download in background thread
        download_future = loop.run_in_executor(
            self._executor,
            lambda: hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=str(local_dir),
            ),
        )

        # Initialize cache monitor
        cache_monitor = CacheMonitor(local_dir, filename)
        initial_incomplete_size = cache_monitor.get_initial_incomplete_size()

        # Monitor progress while downloading
        while not download_future.done():
            if self._cancelled:
                download_future.cancel()
                raise asyncio.CancelledError("Download cancelled by user")

            # Get current file size from cache
            current_size, found_location = cache_monitor.get_current_size()

            # Calculate overall progress
            overall_downloaded, new_bytes_this_session = self._calculate_overall_downloaded(
                current_size, initial_incomplete_size, overall_downloaded_before
            )

            # Send progress update if appropriate
            if progress_callback and cache_monitor.should_send_progress(current_size):
                if current_size > 0:
                    logger.debug(
                        f"Progress update: {current_size}/{file_size} bytes "
                        f"({current_size/file_size*100:.1f}%) from {found_location} "
                        f"(new this session: {new_bytes_this_session:,})"
                    )

                self._send_progress(
                    progress_callback,
                    repo_id,
                    filename,
                    file_idx + 1,
                    total_files,
                    current_size,
                    file_size,
                    overall_downloaded,
                    total_size,
                    start_time,
                )

                cache_monitor.update_tracking(current_size)

            # Log periodic monitoring status
            warning = cache_monitor.log_monitoring_status()
            if warning:
                logger.warning(warning)

            # Sleep briefly before next check
            await asyncio.sleep(PROGRESS_POLL_INTERVAL)

        # Wait for download to complete
        await download_future

        # Send final progress update
        if progress_callback:
            overall_downloaded = overall_downloaded_before + file_size
            self._send_progress(
                progress_callback,
                repo_id,
                filename,
                file_idx + 1,
                total_files,
                file_size,
                file_size,
                overall_downloaded,
                total_size,
                start_time,
            )

    def _calculate_overall_downloaded(
        self, current_size: int, initial_incomplete_size: int, overall_downloaded_before: int
    ) -> tuple[int, int]:
        """
        Calculate total bytes downloaded across all files.

        For resumed downloads:
        - Don't count initial_incomplete_size twice (it's in overall_downloaded_before)
        - Only count NEW bytes downloaded THIS session

        Args:
            current_size: Current size of the incomplete file being monitored
            initial_incomplete_size: Size of incomplete file at start of monitoring
            overall_downloaded_before: Bytes already downloaded from previous files

        Returns:
            Tuple of (overall_downloaded, new_bytes_this_session)
        """
        new_bytes_this_session = current_size - initial_incomplete_size
        overall_downloaded = (
            overall_downloaded_before + initial_incomplete_size + new_bytes_this_session
        )
        return overall_downloaded, new_bytes_this_session

    def _send_progress(
        self,
        callback,
        repo_id,
        filename,
        file_idx,
        total_files,
        file_downloaded,
        file_total,
        overall_downloaded,
        overall_total,
        start_time,
    ):
        """Send progress update to callback with calculated speed and ETA."""
        # Use speed calculator for accurate real-time speed (moving window average)
        speed = self._speed_calculator.update(overall_downloaded) if self._speed_calculator else 0
        remaining = overall_total - overall_downloaded
        eta = calculate_eta(remaining, speed)

        # Determine download status - use flag set during initialization
        status = "resuming" if self._is_resuming and file_idx == 1 else "downloading"
        initial_bytes = self._initial_bytes_before if self._is_resuming else 0

        progress_data: ProgressData = {
            "repo_id": repo_id,
            "current_file": filename,
            "current_file_index": file_idx,
            "total_files": total_files,
            "current_file_downloaded": file_downloaded,
            "current_file_total": file_total,
            "overall_downloaded": overall_downloaded,
            "overall_total": overall_total,
            "speed": speed,
            "eta": eta,
            "status": status,
            "initial_bytes": initial_bytes,
            "completed": False,
        }

        logger.debug(
            f"Progress: {filename} - {file_downloaded}/{file_total} bytes "
            f"(overall: {overall_downloaded}/{overall_total})"
        )
        callback(progress_data)

    def cancel_download(self):
        """Cancel the current download."""
        self._cancelled = True
        logger.info("Download cancellation requested")

    def _calculate_sha256(self, file_path: Path) -> str:
        """
        Calculate SHA256 checksum of a file.

        Args:
            file_path: Path to file to calculate checksum for

        Returns:
            Hexadecimal SHA256 checksum
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _verify_checksum(self, file_path: Path, expected_checksum: Optional[str]) -> bool:
        """
        Verify file checksum against expected value.

        Args:
            file_path: Path to file to verify
            expected_checksum: Expected SHA256 checksum (hex string), or None to skip

        Returns:
            True if checksum matches or no expected checksum, False otherwise

        Raises:
            DownloadError: If file doesn't exist or checksum doesn't match
        """
        if not file_path.exists():
            logger.error(f"File not found for checksum verification: {file_path}")
            raise DownloadError(f"File not found: {file_path}")

        if expected_checksum is None:
            logger.info("No expected checksum provided, skipping verification")
            return True

        logger.info(f"Verifying checksum for {file_path.name}...")
        actual_checksum = self._calculate_sha256(file_path)

        if actual_checksum == expected_checksum:
            logger.info(f"Checksum verified: {file_path.name}")
            return True
        else:
            logger.error(
                f"Checksum mismatch for {file_path.name}: "
                f"expected {expected_checksum[:16]}..., "
                f"got {actual_checksum[:16]}..."
            )
            raise DownloadError(
                f"Checksum mismatch for {file_path.name}. " f"File may be corrupted."
            )

    async def validate_download(
        self, repo_id: str, files: List[str], total_size: int
    ) -> tuple[bool, str]:
        """Validate download can proceed."""
        try:
            # Check disk space on models directory (always exists)
            models_dir = self.storage.models_dir
            stat = shutil.disk_usage(models_dir)
            available_space = stat.free

            # Require 10% buffer
            required_space = int(total_size * 1.1)

            if available_space < required_space:
                return False, (
                    f"Insufficient disk space. "
                    f"Need {required_space / 1024 / 1024 / 1024:.2f} GB, "
                    f"have {available_space / 1024 / 1024 / 1024:.2f} GB available"
                )

            if not files:
                return False, "No files specified for download"

            if "/" not in repo_id:
                return False, f"Invalid repository ID format: {repo_id}"

            logger.info(f"Download validation passed for {repo_id}")
            return True, ""

        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return False, f"Validation failed: {e}"
