"""Download manager with byte-level progress monitoring."""

import asyncio
import logging
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from huggingface_hub import hf_hub_download
from huggingface_hub.constants import HUGGINGFACE_HUB_CACHE

from src.utils.helpers import ProgressCallback, ProgressData

logger = logging.getLogger(__name__)


class DownloadManager:
    """Download manager with byte-level progress tracking."""

    def __init__(self, hf_client, storage_manager):
        """Initialize download manager."""
        self.hf_client = hf_client
        self.storage = storage_manager
        self._cancelled = False
        self._executor = ThreadPoolExecutor(max_workers=1)

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

                    except asyncio.CancelledError:
                        logger.info(f"Download of {filename} cancelled")
                        raise
                    except Exception as e:
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.warning(
                                f"Error downloading {filename} (attempt {retry_count}/{max_retries}): {e}. Retrying..."
                            )
                            # Wait before retrying (exponential backoff)
                            await asyncio.sleep(2**retry_count)
                        else:
                            logger.error(
                                f"Failed to download {filename} after {max_retries} attempts: {e}",
                                exc_info=True,
                            )
                            return False

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
        except Exception as e:
            logger.error(f"Error during download: {e}", exc_info=True)
            return False

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

        # Monitor progress while downloading
        cache_dir = Path(HUGGINGFACE_HUB_CACHE)
        logger.debug(f"Monitoring cache directory: {cache_dir}")

        # Try to find the incomplete file in HF cache
        # HF creates *.incomplete or *.lock files during download
        last_size = 0
        last_update = time.time()

        while not download_future.done():
            if self._cancelled:
                download_future.cancel()
                raise asyncio.CancelledError("Download cancelled by user")

            # Look for the downloading file in cache
            # HF uses complex hash-based paths, so we'll monitor the target location
            target_file = local_dir / filename
            current_size = 0

            # Check if file exists and is growing
            if target_file.exists():
                current_size = target_file.stat().st_size
            else:
                # File might still be in HF cache, look for incomplete files
                # Pattern: .cache/huggingface/download/*.incomplete
                cache_download = cache_dir / "download"
                if cache_download.exists():
                    incomplete_files = list(cache_download.glob("*.incomplete"))
                    if incomplete_files:
                        # Use the most recently modified one
                        incomplete_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                        current_size = incomplete_files[0].stat().st_size

            # Send progress update if size changed or every 500ms
            now = time.time()
            if current_size > last_size or (now - last_update) >= 0.5:
                if progress_callback and current_size > 0:
                    overall_downloaded = overall_downloaded_before + current_size
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
                last_size = current_size
                last_update = now

            # Sleep briefly before next check
            await asyncio.sleep(0.3)

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
        """Send progress update."""
        elapsed = time.time() - start_time
        speed = overall_downloaded / elapsed if elapsed > 0 else 0
        remaining = overall_total - overall_downloaded
        eta = int(remaining / speed) if speed > 0 else 0

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
            "completed": False,
        }

        logger.debug(
            f"Progress: {filename} - {file_downloaded}/{file_total} bytes (overall: {overall_downloaded}/{overall_total})"
        )
        callback(progress_data)

    def cancel_download(self):
        """Cancel the current download."""
        self._cancelled = True
        logger.info("Download cancellation requested")

    async def validate_download(
        self, repo_id: str, files: List[str], total_size: int
    ) -> tuple[bool, str]:
        """Validate download can proceed."""
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

            if not files:
                return False, "No files specified for download"

            if "/" not in repo_id:
                return False, f"Invalid repository ID format: {repo_id}"

            logger.info(f"Download validation passed for {repo_id}")
            return True, ""

        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return False, f"Validation failed: {e}"
