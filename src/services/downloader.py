"""Simplified download manager that actually works."""

import asyncio
import logging
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from huggingface_hub import hf_hub_download

from src.utils.helpers import ProgressCallback, ProgressData

logger = logging.getLogger(__name__)


class DownloadManager:
    """Simplified download manager with reliable progress tracking."""

    def __init__(self, hf_client, storage_manager):
        """Initialize download manager."""
        self.hf_client = hf_client
        self.storage = storage_manager
        self._cancelled = False

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
                                progress_callback, repo_id, filename,
                                idx + 1, len(files), file_size, file_size,
                                overall_downloaded, total_size, start_time
                            )
                        continue

                logger.info(f"Downloading file {idx + 1}/{len(files)}: {filename}")

                # Send "starting" progress
                if progress_callback:
                    self._send_progress(
                        progress_callback, repo_id, filename,
                        idx + 1, len(files), 0, file_size,
                        overall_downloaded, total_size, start_time
                    )

                try:
                    # Download file in thread pool
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        ThreadPoolExecutor(max_workers=1),
                        lambda: hf_hub_download(
                            repo_id=repo_id,
                            filename=filename,
                            local_dir=str(local_dir),
                        ),
                    )

                    # Update overall progress
                    overall_downloaded += file_size

                    # Send "completed" progress
                    if progress_callback:
                        self._send_progress(
                            progress_callback, repo_id, filename,
                            idx + 1, len(files), file_size, file_size,
                            overall_downloaded, total_size, start_time
                        )

                    logger.info(f"Completed download of {filename}")

                except Exception as e:
                    logger.error(f"Error downloading {filename}: {e}", exc_info=True)
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

    def _send_progress(
        self, callback, repo_id, filename, file_idx, total_files,
        file_downloaded, file_total, overall_downloaded, overall_total, start_time
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
        
        logger.info(f"Progress: {filename} - {overall_downloaded}/{overall_total} bytes")
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
