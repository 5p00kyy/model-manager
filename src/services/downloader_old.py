"""Download manager with progress tracking and resume capability."""

import asyncio
import logging
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from huggingface_hub import hf_hub_download

from src.utils.helpers import ProgressCallback, ProgressData, DownloadSpeedCalculator

logger = logging.getLogger(__name__)


class DownloadManager:
    """Manages model downloads with progress tracking."""

    def __init__(self, hf_client, storage_manager):
        """
        Initialize download manager.

        Args:
            hf_client: HuggingFaceClient instance
            storage_manager: StorageManager instance
        """
        self.hf_client = hf_client
        self.storage = storage_manager
        self._cancelled = False
        self._monitor_task = None
        self._current_file_path = None

    async def _download_file_sync(self, repo_id: str, filename: str, local_dir: Path) -> None:
        """
        Synchronous download wrapper for ThreadPoolExecutor.

        Args:
            repo_id: Repository ID
            filename: File to download
            local_dir: Local directory path
        """
        logger.debug(f"Starting sync download: {filename}")
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=str(local_dir),
        )
        logger.debug(f"Completed sync download: {filename}")

    async def _monitor_file_progress(
        self,
        file_path: Path,
        expected_size: int,
        repo_id: str,
        filename: str,
        file_index: int,
        total_files: int,
        overall_downloaded: int,
        total_size: int,
        start_time: float,
        callback: Optional[ProgressCallback],
    ) -> None:
        """
        Monitor file download progress in real-time.

        Args:
            file_path: Path to file being downloaded
            expected_size: Expected file size in bytes
            repo_id: Repository ID
            filename: Current filename
            file_index: Current file index (1-based)
            total_files: Total number of files
            overall_downloaded: Bytes already downloaded (previous files)
            total_size: Total download size
            start_time: Download start timestamp
            callback: Progress callback function
        """
        if not callback or expected_size == 0:
            return

        speed_calc = DownloadSpeedCalculator(window_size=10)
        last_size = 0

        try:
            while not self._cancelled:
                await asyncio.sleep(0.5)  # Update every 500ms

                # Check if file exists and get current size
                if not file_path.exists():
                    continue

                current_size = file_path.stat().st_size

                # Calculate speed
                speed = speed_calc.update(current_size)

                # Calculate progress
                file_progress = current_size
                overall_progress = overall_downloaded + current_size

                # Calculate ETA
                remaining = total_size - overall_progress
                eta = int(remaining / speed) if speed > 0 else 0

                # Send progress update
                progress_data: ProgressData = {
                    "repo_id": repo_id,
                    "current_file": filename,
                    "current_file_index": file_index,
                    "total_files": total_files,
                    "current_file_downloaded": file_progress,
                    "current_file_total": expected_size,
                    "overall_downloaded": overall_progress,
                    "overall_total": total_size,
                    "speed": speed,
                    "eta": eta,
                    "completed": False,
                }

                callback(progress_data)

                # Check if file download is complete
                if current_size >= expected_size and current_size == last_size:
                    logger.debug(f"File {filename} completed: {current_size}/{expected_size} bytes")
                    break

                last_size = current_size

        except Exception as e:
            logger.error(f"Error monitoring progress for {filename}: {e}", exc_info=True)

    async def download_model(
        self, repo_id: str, files: List[str], progress_callback: Optional[ProgressCallback] = None
    ) -> bool:
        """
        Download model files with progress tracking (async).

        Args:
            repo_id: Repository ID
            files: List of filenames to download
            progress_callback: Optional callback function for progress updates
                             Should accept a ProgressData dict

        Returns:
            True if successful, False otherwise

        Note:
            This is an async method that must be awaited. It uses ThreadPoolExecutor
            to run the blocking hf_hub_download in a separate thread while monitoring
            progress asynchronously.
        """
        self._cancelled = False
        local_dir = self.storage.get_model_path(repo_id)
        local_dir.mkdir(parents=True, exist_ok=True)

        # Get file sizes
        logger.debug(f"Fetching file sizes for {repo_id}")
        file_sizes = self.hf_client.get_file_sizes(repo_id)
        total_size = sum(file_sizes.get(f, 0) for f in files)

        logger.info(
            f"Starting download: repo={repo_id}, files={len(files)}, "
            f"total_size={total_size:,} bytes ({total_size / 1024 / 1024:.1f} MB)"
        )

        overall_downloaded = 0
        start_time = time.time()

        try:
            for idx, filename in enumerate(files):
                if self._cancelled:
                    logger.info("Download cancelled by user")
                    return False

                file_size = file_sizes.get(filename, 0)
                file_path = local_dir / filename
                self._current_file_path = file_path

                # Check if file already exists
                if file_path.exists():
                    existing_size = file_path.stat().st_size
                    if existing_size == file_size and file_size > 0:
                        logger.info(f"File {filename} already exists with correct size, skipping")
                        overall_downloaded += file_size
                        continue
                    else:
                        logger.info(
                            f"File {filename} exists but size mismatch "
                            f"(have {existing_size}, need {file_size}), re-downloading"
                        )

                logger.info(
                    f"Downloading file {idx + 1}/{len(files)}: {filename} " f"({file_size:,} bytes)"
                )

                try:
                    # Start progress monitoring task
                    monitor_task = None
                    if progress_callback and file_size > 0:
                        monitor_task = asyncio.create_task(
                            self._monitor_file_progress(
                                file_path=file_path,
                                expected_size=file_size,
                                repo_id=repo_id,
                                filename=filename,
                                file_index=idx + 1,
                                total_files=len(files),
                                overall_downloaded=overall_downloaded,
                                total_size=total_size,
                                start_time=start_time,
                                callback=progress_callback,
                            )
                        )
                        self._monitor_task = monitor_task

                    # Download file in thread pool (non-blocking)
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        ThreadPoolExecutor(max_workers=1),
                        lambda: hf_hub_download(
                            repo_id=repo_id,
                            filename=filename,
                            local_dir=str(local_dir),
                        ),
                    )

                    # Cancel monitoring task
                    if monitor_task:
                        monitor_task.cancel()
                        try:
                            await monitor_task
                        except asyncio.CancelledError:
                            pass

                    # Update overall progress
                    if file_size > 0:
                        overall_downloaded += file_size

                    # Send final progress update for this file
                    if progress_callback:
                        elapsed = time.time() - start_time
                        speed = overall_downloaded / elapsed if elapsed > 0 else 0
                        remaining = total_size - overall_downloaded
                        eta = int(remaining / speed) if speed > 0 else 0

                        progress_data: ProgressData = {
                            "repo_id": repo_id,
                            "current_file": filename,
                            "current_file_index": idx + 1,
                            "total_files": len(files),
                            "current_file_downloaded": file_size,
                            "current_file_total": file_size,
                            "overall_downloaded": overall_downloaded,
                            "overall_total": total_size,
                            "speed": speed,
                            "eta": eta,
                            "completed": False,
                        }
                        progress_callback(progress_data)

                    logger.info(f"Completed download of {filename}")

                except Exception as e:
                    logger.error(f"Error downloading {filename}: {e}", exc_info=True)
                    return False

            # Get commit SHA and save metadata
            logger.debug(f"Fetching commit SHA for {repo_id}")
            commit_sha = self.hf_client.get_commit_sha(repo_id)
            self.storage.save_model_metadata(repo_id, commit_sha)

            # Final progress callback
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
            logger.info(
                f"Download completed: repo={repo_id}, "
                f"duration={elapsed:.2f}s, "
                f"avg_speed={overall_downloaded / elapsed / 1024 / 1024:.2f} MB/s"
            )
            return True

        except asyncio.CancelledError:
            logger.info("Download cancelled")
            return False
        except Exception as e:
            logger.error(f"Error during download of {repo_id}: {e}", exc_info=True)
            return False

    def cancel_download(self):
        """Cancel the current download."""
        self._cancelled = True
        logger.info("Download cancellation requested")

        # Cancel monitoring task if running
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()

    async def validate_download(
        self, repo_id: str, files: List[str], total_size: int
    ) -> tuple[bool, str]:
        """
        Validate download can proceed.

        Args:
            repo_id: Repository ID
            files: List of files to download
            total_size: Total download size in bytes

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Check disk space
            local_dir = self.storage.get_model_path(repo_id)
            stat = shutil.disk_usage(local_dir.parent)
            available_space = stat.free

            # Require 10% buffer
            required_space = int(total_size * 1.1)

            if available_space < required_space:
                return False, (
                    f"Insufficient disk space. "
                    f"Need {required_space / 1024 / 1024 / 1024:.2f} GB, "
                    f"have {available_space / 1024 / 1024 / 1024:.2f} GB available"
                )

            # Validate files list
            if not files:
                return False, "No files specified for download"

            # Validate repo_id format
            if "/" not in repo_id:
                return False, f"Invalid repository ID format: {repo_id}"

            logger.info(
                f"Download validation passed: "
                f"space={available_space / 1024 / 1024 / 1024:.2f} GB available, "
                f"need={required_space / 1024 / 1024 / 1024:.2f} GB"
            )

            return True, ""

        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return False, f"Validation failed: {e}"
