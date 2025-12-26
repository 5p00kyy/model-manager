# Agent Guide for Model Manager

This guide provides agentic coding assistants (Cursor, Copilot, etc.) with the conventions, tools, and workflows used in the Model Manager codebase.

---

## Quick Reference

**Test Single File:**
```bash
python3 -m pytest tests/test_downloader.py -v -k "test_name"
```

**Lint & Format:**
```bash
python3 -m black src/ --line-length 100
python3 -m flake8 src/ --max-line-length=100 --extend-ignore=E203,W503
python3 -m mypy src/
```

**Run All Tests:**
```bash
python3 -m pytest tests/ -v
```

---

## Code Style Guidelines

### Import Order

1. Standard library imports first
2. Third-party imports second
3. Internal imports with `src.` prefix last
4. Group imports alphabetically within each section

```python
import asyncio
import logging
import time

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from huggingface_hub import hf_hub_download
from huggingface_hub.constants import HUGGINGFACE_HUB_CACHE

from src.utils.helpers import ProgressCallback, ProgressData, DownloadSpeedCalculator
from src.services.hf_client import HuggingFaceClient
```

### Naming Conventions

**Classes:** PascalCase
```python
class DownloadManager:
class DownloadSpeedCalculator:
class ModelManagerApp:
```

**Functions & Variables:** snake_case
```python
def download_model():
def calculate_eta():
def update_progress():
```

**Private Members:** Leading underscore
```python
self._cancelled
self._speed_calculator
self._is_resuming
```

**Constants:** UPPER_SNAKE_CASE
```python
MAX_SEARCH_RESULTS = 50
UPDATE_CHECK_TIMEOUT = 10
CACHE_DURATION = 300
```

### Formatting

**Code Formatter:** Black
- Line length: 100 characters
- No trailing whitespace
- Consistent indentation (4 spaces)

```bash
# Format all code
python3 -m black src/ --line-length 100
```

**String Formatting:** f-strings preferred
```python
logger.info(f"Downloading {filename}")
progress_label.update(f"{downloaded} / {total}")
```

**Docstrings:** Google style (triple quotes)
```python
def format_size(bytes_size: float) -> str:
    """
    Format bytes into human-readable size.

    Args:
        bytes_size: Size in bytes

    Returns:
        Formatted string (e.g., "4.2 GB")
    """
```

### Type Hints

**Always include type hints** for function parameters and return types:
```python
from typing import List, Optional, TypedDict, Callable

def download_model(
    self, repo_id: str, files: List[str], progress_callback: Optional[ProgressCallback] = None
) -> bool:
```

**Use TypedDict for complex dictionaries:**
```python
from typing import TypedDict

class ProgressData(TypedDict, total=False):
    repo_id: str
    current_file: str
    speed: float
    # ... other fields
```

**Use Optional for nullable parameters:**
```python
progress_callback: Optional[ProgressCallback] = None
```

---

## Error Handling

### Exception Hierarchy

Use specific exception types, not generic Exception:
```python
# Custom exceptions in src/exceptions.py
class ModelManagerException(Exception):
    pass

class DownloadError(ModelManagerException):
    pass

class HuggingFaceError(ModelManagerException):
    pass
```

### Exception Handling Pattern

Always log with `exc_info=True` for debugging:
```python
try:
    await self._download_with_progress(...)
except DownloadError as e:
    logger.error(f"DownloadError: {e}", exc_info=True)
    self.update_error(str(e))
except asyncio.CancelledError:
    logger.info("Download cancelled")
    return False
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    self.update_error(f"Unexpected error: {e}")
```

### Error Logging Levels

- **DEBUG:** Detailed implementation details, progress updates
- **INFO:** Normal operations, user actions
- **WARNING:** Non-critical issues, retry attempts
- **ERROR:** Failures and exceptions

```python
logger.debug(f"Progress update: {current_size}/{file_size} bytes")
logger.info(f"Starting download: {repo_id}")
logger.warning(f"Retrying download (attempt {retry_count}/{max_retries})")
logger.error(f"Download failed: {e}", exc_info=True)
```

---

## Async Patterns

### Async Function Definition

Use `async def` for coroutines:
```python
async def download_model(self, repo_id: str, files: List[str]) -> bool:
```

### Async Function Calls

Use `await` for async calls:
```python
success = await app.downloader.download_model(repo_id, files, callback)
```

### Run Sync in Thread Pool

Use `run_in_executor` for blocking operations:
```python
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=1)
download_future = loop.run_in_executor(
    executor,
    lambda: hf_hub_download(repo_id=repo_id, filename=filename)
)
```

### Async Testing

Mark async tests with `@pytest.mark.asyncio`:
```python
@pytest.mark.asyncio
async def test_download_success(downloader):
    success = await downloader.download_model(...)
    assert success is True
```

---

## Testing Guidelines

### Test Structure

Use pytest with fixtures:
```python
class TestDownloadManager:
    """Test suite for DownloadManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def downloader(self, mock_hf_client, mock_storage):
        """Create a DownloadManager instance."""
        return DownloadManager(mock_hf_client, mock_storage)
```

### Mock Patterns

Use `unittest.mock.Mock` for mocking:
```python
from unittest.mock import Mock, AsyncMock, patch, MagicMock

client = Mock()
client.get_file_sizes = Mock(return_value={"test.gguf": 1024})
```

### Test Naming

Use descriptive names starting with `test_`:
```python
def test_initialization(self, downloader):
def test_validate_download_success(self, downloader):
def test_progress_data_structure(self, downloader):
def test_speed_calculator_window_size(self):
```

### Running Tests

**Single test:**
```bash
python3 -m pytest tests/test_downloader.py::TestDownloadManager::test_initialization -v
```

**All tests in file:**
```bash
python3 -m pytest tests/test_downloader.py -v
```

**All tests in directory:**
```bash
python3 -m pytest tests/ -v
```

**Run with coverage:**
```bash
python3 -m pytest tests/ --cov=src --cov-report=html
```

---

## Logging Guidelines

### Logger Setup

Create logger at module level:
```python
import logging

logger = logging.getLogger(__name__)
```

### Log Format

Configure logging at application level (in `src/app.py`):
```python
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
```

### Log Messages

Be descriptive and include context:
```python
logger.info(f"Starting download: repo={repo_id}, files={len(files)}")
logger.debug(f"Progress update: {current_size}/{file_size} bytes ({pct:.1f}%)")
logger.error(f"Download failed: {repo_id}", exc_info=True)
```

### Structured Data

Use f-strings for consistent formatting:
```python
# Good
logger.info(f"Downloading {filename} - {speed:.1f} MB/s")

# Avoid
logger.info("Downloading " + filename + " - " + str(speed) + " MB/s")
```

---

## UI/Screen Guidelines

### Screen Structure

Inherit from `textual.screen.Screen`:
```python
from textual.screen import Screen
from textual.app import ComposeResult

class DownloadScreen(Screen):
    """Screen showing download progress."""
```

### Widget Querying

Use `query_one()` to get widgets by ID:
```python
table = self.query_one("#quant-table", DataTable)
label = self.query_one("#progress-label", Label)
```

### Widget Guards

Always guard against updates after unmount:
```python
def update_progress(self, progress_data: dict):
    if not self._is_mounted:
        return
    # Safe to update widgets
```

### Lifecycle Handlers

Implement `on_mount()` and `on_unmount()`:
```python
def on_mount(self) -> None:
    """Handle screen mount."""
    self._is_mounted = True

def on_unmount(self) -> None:
    """Handle screen unmount."""
    self._is_mounted = False
```

---

## File Operations

### Path Handling

Use `pathlib.Path` for file operations:
```python
from pathlib import Path

model_dir = Path("/path/to/models")
file_path = model_dir / "model.gguf"
```

### Directory Creation

Use `mkdir()` with error handling:
```python
local_dir.mkdir(parents=True, exist_ok=True)
```

### File Size

Use `stat().st_size` to get file size:
```python
file_size = (local_dir / filename).stat().st_size
```

---

## Code Review Checklist

When modifying code, ensure:

- [ ] Code formatted with `black --line-length 100`
- [ ] Type hints added for all functions
- [ ] Error handling includes `exc_info=True`
- [ ] Specific exceptions used, not generic `Exception`
- [ ] Logger created with `logging.getLogger(__name__)`
- [ ] Docstrings added for new functions/classes
- [ ] Tests added/updated for new functionality
- [ ] Import order maintained (stdlib, third-party, src)
- [ ] No trailing whitespace
- [ ] f-strings used instead of concatenation
- [ ] Private methods prefixed with underscore

---

## Common Patterns

### Progress Callback Pattern

```python
from typing import TypedDict, Callable

class ProgressData(TypedDict, total=False):
    repo_id: str
    current_file: str
    speed: float
    eta: int

ProgressCallback = Callable[[ProgressData], None]

def some_function(callback: Optional[ProgressCallback] = None):
    if callback:
        progress_data = ProgressData(...)
        callback(progress_data)
```

### Resource Management Pattern

```python
def on_mount(self):
    # Initialize resources
    pass

def on_unmount(self):
    # Cleanup resources
    pass
```

### Validation Pattern

```python
async def validate_download(self, repo_id: str, files: List[str], total_size: int) -> tuple[bool, str]:
    """Validate download can proceed."""
    try:
        # Validation logic
        return True, ""
    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return False, f"Validation failed: {e}"
```

---

## Development Commands

### Format Code
```bash
# Format specific file
python3 -m black src/services/downloader.py --line-length 100

# Format all src/
python3 -m black src/ --line-length 100

# Check what would be formatted
python3 -m black --check src/
```

### Lint Code
```bash
# Lint specific file
python3 -m flake8 src/services/downloader.py --max-line-length=100

# Lint all src/
python3 -m flake8 src/ --max-line-length=100 --extend-ignore=E203,W503
```

### Type Check
```bash
# Type check specific file
python3 -m mypy src/services/downloader.py

# Type check all src/
python3 -m mypy src/
```

### Sort Imports
```bash
# Sort imports in all files
python3 -m isort src/
```

---

## Project-Specific Patterns

### Download Progress Tracking

The codebase uses byte-level progress monitoring:

1. **Track incomplete file size** before monitoring starts
2. **Calculate new bytes this session** to fix resumed download bug
3. **Use speed calculator** with moving window average
4. **Filter zero-delta samples** to prevent 0 speed

```python
# Track initial size
initial_incomplete_size = 0
if target_file.exists():
    initial_incomplete_size = target_file.stat().st_size

# Calculate new bytes only
new_bytes_this_session = current_size - initial_incomplete_size
overall_downloaded = initial_incomplete_size + new_bytes_this_session
```

### Screen Navigation

The codebase uses smart navigation patterns:

1. **Auto-focus tables** after loading
2. **Enter key support** on table rows
3. **Arrow key switching** between widgets
4. **Minimal Tab presses** required

```python
# Auto-focus after loading
self.call_after_refresh(self._focus_quant_table)

# Handle Enter on table
def on_data_table_row_selected(self, event):
    self.action_download()

# Smart arrow navigation
def on_key(self, event):
    if event.key == "down" and button.has_focus:
        table.focus()
```

---

## Tools & Dependencies

**Code Quality:**
- Black: Code formatting
- Flake8: Linting
- Mypy: Type checking
- isort: Import sorting

**Testing:**
- pytest: Test framework
- pytest-asyncio: Async test support
- pytest-mock: Test fixtures
- pytest-cov: Coverage reports

**Documentation:**
- Sphinx: Documentation generation
- sphinx-rtd-theme: Read the Docs theme

---

## Summary

This codebase follows professional Python conventions with:

1. **Consistent formatting** via Black (100 char lines)
2. **Type safety** via mypy and type hints
3. **Comprehensive testing** with pytest
4. **Proper error handling** with detailed logging
5. **Clean async patterns** using asyncio
6. **Modular design** with services, screens, and widgets
7. **Resource management** with proper lifecycle handling

When working with this codebase:
- Always use Black for formatting
- Add type hints to new code
- Include tests for new features
- Log with exc_info=True for errors
- Follow import order and naming conventions

This ensures code quality, maintainability, and consistency across contributions.
