"""Tests for helper utilities."""

import time
import pytest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.helpers import (
    format_size,
    format_speed,
    format_time,
    parse_multipart_filename,
    group_multipart_files,
    DownloadSpeedCalculator,
    calculate_eta,
)


class TestFormatSize:
    """Test suite for format_size function."""

    def test_format_bytes(self):
        """Test formatting bytes."""
        assert format_size(0) == "0.0 B"
        assert format_size(512) == "512.0 B"
        assert format_size(1023) == "1023.0 B"

    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_size(1024) == "1.0 KB"
        assert format_size(1536) == "1.5 KB"
        assert format_size(10240) == "10.0 KB"

    def test_format_megabytes(self):
        """Test formatting megabytes."""
        assert format_size(1024 * 1024) == "1.0 MB"
        assert format_size(1024 * 1024 * 5.5) == "5.5 MB"
        assert format_size(1024 * 1024 * 100) == "100.0 MB"

    def test_format_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_size(1024**3) == "1.0 GB"
        assert format_size(1024**3 * 7.2) == "7.2 GB"

    def test_format_terabytes(self):
        """Test formatting terabytes."""
        assert format_size(1024**4) == "1.0 TB"
        assert format_size(1024**4 * 2.5) == "2.5 TB"

    def test_format_petabytes(self):
        """Test formatting petabytes."""
        assert format_size(1024**5) == "1.0 PB"


class TestFormatSpeed:
    """Test suite for format_speed function."""

    def test_format_zero_speed(self):
        """Test formatting zero speed."""
        assert format_speed(0) == "0 B/s"

    def test_format_bytes_per_second(self):
        """Test formatting bytes per second."""
        assert format_speed(512) == "512.0 B/s"
        assert format_speed(1000) == "1000.0 B/s"

    def test_format_kilobytes_per_second(self):
        """Test formatting KB/s."""
        assert format_speed(1024) == "1.0 KB/s"
        assert format_speed(1024 * 500) == "500.0 KB/s"

    def test_format_megabytes_per_second(self):
        """Test formatting MB/s."""
        assert format_speed(1024 * 1024) == "1.0 MB/s"
        assert format_speed(1024 * 1024 * 10) == "10.0 MB/s"
        assert format_speed(1024 * 1024 * 100) == "100.0 MB/s"

    def test_format_gigabytes_per_second(self):
        """Test formatting GB/s."""
        assert format_speed(1024**3) == "1.0 GB/s"


class TestFormatTime:
    """Test suite for format_time function."""

    def test_format_seconds(self):
        """Test formatting seconds."""
        assert format_time(0) == "0s"
        assert format_time(30) == "30s"
        assert format_time(59) == "59s"

    def test_format_minutes(self):
        """Test formatting minutes."""
        assert format_time(60) == "1m 0s"
        assert format_time(90) == "1m 30s"
        assert format_time(3599) == "59m 59s"

    def test_format_hours(self):
        """Test formatting hours."""
        assert format_time(3600) == "1h 0m"
        assert format_time(3660) == "1h 1m"
        assert format_time(7200) == "2h 0m"
        assert format_time(86399) == "23h 59m"

    def test_format_days(self):
        """Test formatting days."""
        assert format_time(86400) == "1d 0h"
        assert format_time(86400 + 3600) == "1d 1h"
        assert format_time(86400 * 7) == "7d 0h"

    def test_format_negative(self):
        """Test formatting negative time."""
        assert format_time(-1) == "unknown"

    def test_format_float(self):
        """Test formatting float seconds."""
        assert format_time(30.5) == "30s"
        assert format_time(90.9) == "1m 30s"


class TestParseMultipartFilename:
    """Test suite for parse_multipart_filename function."""

    def test_parse_valid_multipart(self):
        """Test parsing valid multipart filename."""
        result = parse_multipart_filename("model-Q4_K_M-00001-of-00005.gguf")

        assert result is not None
        assert result[0] == "model-Q4_K_M"
        assert result[1] == 1
        assert result[2] == 5

    def test_parse_multipart_middle_part(self):
        """Test parsing middle part of multipart file."""
        result = parse_multipart_filename("model-00003-of-00010.gguf")

        assert result is not None
        assert result[0] == "model"
        assert result[1] == 3
        assert result[2] == 10

    def test_parse_non_multipart(self):
        """Test parsing non-multipart filename."""
        result = parse_multipart_filename("model-Q4_K_M.gguf")

        assert result is None

    def test_parse_non_gguf(self):
        """Test parsing non-GGUF file."""
        result = parse_multipart_filename("model-00001-of-00002.bin")

        assert result is None

    def test_parse_invalid_format(self):
        """Test parsing invalid format."""
        result = parse_multipart_filename("model.gguf")

        assert result is None


class TestGroupMultipartFiles:
    """Test suite for group_multipart_files function."""

    def test_group_multipart_files(self):
        """Test grouping multipart files."""
        files = [
            "model-Q4_K_M-00001-of-00003.gguf",
            "model-Q4_K_M-00002-of-00003.gguf",
            "model-Q4_K_M-00003-of-00003.gguf",
        ]

        groups = group_multipart_files(files)

        assert len(groups) == 1
        assert "model-Q4_K_M" in groups
        assert len(groups["model-Q4_K_M"]) == 3

    def test_group_single_files(self):
        """Test grouping single (non-multipart) files."""
        files = ["model-Q4.gguf", "model-Q5.gguf"]

        groups = group_multipart_files(files)

        assert len(groups) == 2
        assert "model-Q4.gguf" in groups
        assert "model-Q5.gguf" in groups

    def test_group_mixed_files(self):
        """Test grouping mixed multipart and single files."""
        files = [
            "model-Q4-00001-of-00002.gguf",
            "model-Q4-00002-of-00002.gguf",
            "model-Q5.gguf",
        ]

        groups = group_multipart_files(files)

        assert len(groups) == 2
        assert "model-Q4" in groups
        assert len(groups["model-Q4"]) == 2
        assert "model-Q5.gguf" in groups
        assert len(groups["model-Q5.gguf"]) == 1

    def test_group_files_sorted(self):
        """Test that files are sorted within groups."""
        files = [
            "model-00003-of-00003.gguf",
            "model-00001-of-00003.gguf",
            "model-00002-of-00003.gguf",
        ]

        groups = group_multipart_files(files)

        assert groups["model"] == [
            "model-00001-of-00003.gguf",
            "model-00002-of-00003.gguf",
            "model-00003-of-00003.gguf",
        ]

    def test_group_empty_list(self):
        """Test grouping empty list."""
        groups = group_multipart_files([])

        assert groups == {}


class TestCalculateEta:
    """Test suite for calculate_eta function."""

    def test_calculate_eta_normal(self):
        """Test normal ETA calculation."""
        # 100 MB remaining at 10 MB/s = 10 seconds
        remaining = 100 * 1024 * 1024
        speed = 10 * 1024 * 1024

        eta = calculate_eta(remaining, speed)

        assert eta == 10

    def test_calculate_eta_zero_speed(self):
        """Test ETA with zero speed."""
        eta = calculate_eta(1000000, 0)

        assert eta == 0

    def test_calculate_eta_negative_speed(self):
        """Test ETA with negative speed."""
        eta = calculate_eta(1000000, -100)

        assert eta == 0

    def test_calculate_eta_large_remaining(self):
        """Test ETA with large remaining bytes."""
        # 10 GB remaining at 1 MB/s = ~10000 seconds
        remaining = 10 * 1024**3
        speed = 1 * 1024**2

        eta = calculate_eta(remaining, speed)

        assert eta == 10240  # 10 GB / 1 MB/s


class TestDownloadSpeedCalculator:
    """Test suite for DownloadSpeedCalculator class."""

    def test_initialization(self):
        """Test calculator initialization."""
        calc = DownloadSpeedCalculator(window_size=5)

        assert calc.window_size == 5
        assert len(calc.samples) == 0

    def test_initialization_default_window(self):
        """Test default window size."""
        calc = DownloadSpeedCalculator()

        assert calc.window_size == 10

    def test_single_sample_returns_zero(self):
        """Test that single sample returns zero speed."""
        calc = DownloadSpeedCalculator()

        speed = calc.update(1024)

        assert speed == 0.0

    def test_two_samples_calculates_speed(self):
        """Test speed calculation with two samples."""
        calc = DownloadSpeedCalculator()

        calc.update(0)
        time.sleep(0.1)
        speed = calc.update(1024)

        # Should be approximately 10240 B/s (1024 bytes / 0.1 seconds)
        assert speed > 0

    def test_multiple_samples(self):
        """Test speed with multiple samples."""
        calc = DownloadSpeedCalculator(window_size=5)

        speeds = []
        for i in range(10):
            speed = calc.update(i * 1024)
            speeds.append(speed)
            time.sleep(0.01)

        # Later samples should show consistent speed
        assert speeds[-1] > 0

    def test_window_size_limit(self):
        """Test that samples are limited to window size."""
        calc = DownloadSpeedCalculator(window_size=3)

        for i in range(10):
            calc.update(i * 1024)

        assert len(calc.samples) <= 3

    def test_reset(self):
        """Test calculator reset."""
        calc = DownloadSpeedCalculator()

        calc.update(1024)
        calc.update(2048)
        assert len(calc.samples) > 0

        calc.reset()
        assert len(calc.samples) == 0

    def test_zero_byte_delta(self):
        """Test handling of zero byte delta (stalled download)."""
        calc = DownloadSpeedCalculator()

        calc.update(1024)
        time.sleep(0.01)
        calc.update(1024)  # Same value - no progress
        time.sleep(0.01)
        speed = calc.update(1024)

        # Speed should be 0 or use fallback
        assert speed >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
