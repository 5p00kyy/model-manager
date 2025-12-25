#!/usr/bin/env python3
"""Entry point for Model Manager application."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.app import run

if __name__ == "__main__":
    run()
