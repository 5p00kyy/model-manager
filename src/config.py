"""Configuration and constants for the Model Manager."""

import os
from pathlib import Path

# Application metadata
APP_NAME = "Model Manager"
APP_VERSION = "2.3.0"

# Directory paths
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "models"
METADATA_FILE = MODELS_DIR / ".metadata.json"
LOG_FILE = BASE_DIR / "model_manager.log"

# Ensure models directory exists
MODELS_DIR.mkdir(exist_ok=True)

# HuggingFace settings
GGUF_TAG = "gguf"
MAX_SEARCH_RESULTS = 50
MULTIPART_REGEX = r"(.+)-(\d{1,5})-of-(\d{1,5})\.gguf$"

# Enable faster downloads (requires hf_transfer package)
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

# Update checking settings
UPDATE_CHECK_TIMEOUT = 10  # seconds per model
CACHE_DURATION = 300  # 5 minutes for API response caching

# Download settings
CHUNK_SIZE = 8192  # 8KB chunks for progress updates
DISK_SPACE_BUFFER = 1.1  # 10% buffer for disk space checks

# UI settings
DEBOUNCE_DELAY = 0.5  # seconds for search input debouncing
PROGRESS_UPDATE_RATE = 10  # Hz for progress bar updates
