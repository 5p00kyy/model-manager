"""Helper utility functions."""

import re
import time
from typing import Dict, List, Optional, Tuple, TypedDict, Callable


# Type definitions for download progress
class ProgressData(TypedDict, total=False):
    """Structure for download progress updates."""
    repo_id: str
    current_file: str
    current_file_index: int
    total_files: int
    current_file_downloaded: int
    current_file_total: int
    overall_downloaded: int
    overall_total: int
    speed: float
    eta: int
    completed: bool
    retry: int
    max_retries: int


# Type alias for progress callback
ProgressCallback = Callable[[ProgressData], None]


# Regex pattern for multipart GGUF files
MULTIPART_REGEX = r"(.+)-(\d{1,5})-of-(\d{1,5})\.gguf$"


def format_size(bytes_size: float) -> str:
    """
    Format bytes into human-readable size.

    Args:
        bytes_size: Size in bytes

    Returns:
        Formatted string (e.g., "4.2 GB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def format_speed(bytes_per_sec: float) -> str:
    """
    Format download speed into human-readable format.

    Args:
        bytes_per_sec: Speed in bytes per second

    Returns:
        Formatted string (e.g., "12.5 MB/s")
    """
    if bytes_per_sec == 0:
        return "0 B/s"

    for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
        if bytes_per_sec < 1024.0:
            return f"{bytes_per_sec:.1f} {unit}"
        bytes_per_sec /= 1024.0
    return f"{bytes_per_sec:.1f} TB/s"


def format_time(seconds: float) -> str:
    """
    Format time in seconds to human-readable format.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted string (e.g., "3m 42s", "1h 23m")
    """
    if seconds < 0:
        return "unknown"

    seconds = int(seconds)

    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    secs = seconds % 60

    if minutes < 60:
        return f"{minutes}m {secs}s"

    hours = minutes // 60
    mins = minutes % 60

    if hours < 24:
        return f"{hours}h {mins}m"

    days = hours // 24
    hrs = hours % 24
    return f"{days}d {hrs}h"


def parse_multipart_filename(filename: str) -> Optional[Tuple[str, int, int]]:
    """
    Parse a multipart GGUF filename.

    Args:
        filename: The filename to parse

    Returns:
        Tuple of (base_name, part_number, total_parts) or None if not multipart

    Example:
        "model-Q4_K_M-00001-of-00005.gguf" -> ("model-Q4_K_M", 1, 5)
    """
    match = re.match(MULTIPART_REGEX, filename)
    if match:
        base_name = match.group(1)
        part_num = int(match.group(2))
        total_parts = int(match.group(3))
        return (base_name, part_num, total_parts)
    return None


def group_multipart_files(files: List[str]) -> Dict[str, List[str]]:
    """
    Group GGUF files by their base name, combining multipart files.

    Args:
        files: List of GGUF filenames

    Returns:
        Dictionary mapping base names to list of files

    Example:
        ["model-Q4_K_M-00001-of-00002.gguf", "model-Q4_K_M-00002-of-00002.gguf",
         "other-Q5_K_S.gguf"]
        ->
        {"model-Q4_K_M": ["model-Q4_K_M-00001-of-00002.gguf",
                          "model-Q4_K_M-00002-of-00002.gguf"],
         "other-Q5_K_S.gguf": ["other-Q5_K_S.gguf"]}
    """
    groups: Dict[str, List[str]] = {}

    for file in files:
        parsed = parse_multipart_filename(file)
        if parsed:
            base_name, _, _ = parsed
            if base_name not in groups:
                groups[base_name] = []
            groups[base_name].append(file)
        else:
            # Single file, use full name as key
            groups[file] = [file]

    # Sort files within each group
    for key in groups:
        groups[key] = sorted(groups[key])

    return groups


class DownloadSpeedCalculator:
    """Calculate download speed with moving average."""

    def __init__(self, window_size: int = 10):
        """
        Initialize speed calculator.

        Args:
            window_size: Number of samples for moving average
        """
        self.window_size = window_size
        self.samples: List[Tuple[float, int]] = []  # (timestamp, bytes)
        self.start_time = time.time()
        self.start_bytes = 0

    def update(self, current_bytes: int) -> float:
        """
        Update with current byte count and get current speed.

        Args:
            current_bytes: Total bytes downloaded so far

        Returns:
            Current speed in bytes per second
        """
        current_time = time.time()
        self.samples.append((current_time, current_bytes))

        # Keep only recent samples
        if len(self.samples) > self.window_size:
            self.samples.pop(0)

        # Need at least 2 samples to calculate speed
        if len(self.samples) < 2:
            return 0.0

        # Calculate speed from first to last sample in window
        first_time, first_bytes = self.samples[0]
        last_time, last_bytes = self.samples[-1]

        time_diff = last_time - first_time
        if time_diff == 0:
            return 0.0

        bytes_diff = last_bytes - first_bytes
        return bytes_diff / time_diff

    def reset(self):
        """Reset the speed calculator."""
        self.samples.clear()
        self.start_time = time.time()


def calculate_eta(remaining_bytes: int, speed: float) -> int:
    """
    Calculate estimated time remaining.

    Args:
        remaining_bytes: Bytes left to download
        speed: Current speed in bytes per second

    Returns:
        Estimated seconds remaining
    """
    if speed <= 0:
        return 0
    return int(remaining_bytes / speed)
