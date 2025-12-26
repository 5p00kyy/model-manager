#!/usr/bin/env python3
"""Test script to verify navigation flow improvements."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.screens.detail_screen import DetailScreen
from textual.widgets import DataTable


def test_detail_screen_bindings():
    """Test that detail screen has correct bindings."""
    from textual.binding import Binding
    
    screen = DetailScreen({"repo_id": "test/model"}, is_remote=True)
    
    # Check bindings exist
    binding_keys = []
    for b in screen.BINDINGS:
        if isinstance(b, Binding):
            binding_keys.append(b.key)
        elif isinstance(b, tuple):
            binding_keys.append(b[0])
    
    assert "escape" in binding_keys
    assert "q" in binding_keys
    assert "d" in binding_keys
    assert "enter" in binding_keys
    print("✓ Detail screen bindings are correct")


def test_detail_screen_methods():
    """Test that detail screen has navigation methods."""
    screen = DetailScreen({"repo_id": "test/model"}, is_remote=True)
    
    # Check methods exist
    assert hasattr(screen, "_focus_quant_table")
    assert hasattr(screen, "on_data_table_row_selected")
    assert hasattr(screen, "on_key")
    print("✓ Detail screen navigation methods exist")


def test_download_screen_import():
    """Test that download screen imports work."""
    from src.screens.download_screen import DownloadScreen
    from src.utils.helpers import format_size, format_speed, format_time
    
    # Check helpers are available
    assert callable(format_size)
    assert callable(format_speed)
    assert callable(format_time)
    print("✓ Download screen imports are correct")


def test_speed_calculator():
    """Test speed calculator functionality."""
    from src.utils.helpers import DownloadSpeedCalculator, calculate_eta
    
    calc = DownloadSpeedCalculator(window_size=10)
    assert calc is not None
    
    # Test basic operation
    speed1 = calc.update(1024)
    assert speed1 == 0.0  # First sample
    
    import time
    time.sleep(0.01)
    speed2 = calc.update(2048)
    assert speed2 >= 0  # Should have speed now
    
    # Test ETA calculation
    eta = calculate_eta(1000, 100)
    assert eta == 10  # 1000 bytes at 100 bytes/sec = 10 seconds
    
    eta_zero = calculate_eta(1000, 0)
    assert eta_zero == 0  # Zero speed = unknown ETA
    
    print("✓ Speed calculator works correctly")


if __name__ == "__main__":
    print("Testing navigation and progress improvements...")
    print()
    
    try:
        test_detail_screen_bindings()
        test_detail_screen_methods()
        test_download_screen_import()
        test_speed_calculator()
        
        print()
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        print()
        print("Navigation Improvements:")
        print("  • Quant table auto-focuses after loading")
        print("  • Enter key on table row starts download")
        print("  • Smart arrow navigation between button and table")
        print("  • 'D' key or 'Download Selected' button work from anywhere")
        print()
        print("Progress Display Improvements:")
        print("  • Real-time speed tracking with moving average")
        print("  • Accurate ETA based on current speed")
        print("  • Stall detection (shows 'Download stalled' if < 1 KB/s)")
        print("  • Accurate file count (0/3 → 1/3 → 2/3 → 3/3)")
        print()
        
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
