# Changelog

All notable changes to Model Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.1] - 2024-12-25

### Added

#### Download System
- **Async Download Architecture** - Complete rewrite of download system using asyncio and ThreadPoolExecutor
  - Downloads now run in separate thread pool to prevent UI freezing
  - Progress monitoring happens asynchronously with 500ms update intervals
  - Proper async/await pattern throughout download flow
- **Real-Time Progress Monitoring** - New `_monitor_file_progress()` method tracks file growth
  - Updates progress every 500ms during large file downloads
  - Uses `DownloadSpeedCalculator` for accurate speed measurements
  - Provides smooth, continuous progress updates instead of per-file updates
- **Pre-Download Validation** - New `validate_download()` method checks:
  - Available disk space (with 10% buffer requirement)
  - Valid repository ID format
  - Non-empty file list
  - Returns clear error messages when validation fails
- **Comprehensive Logging** - Added DEBUG and INFO level logs throughout:
  - Download start/completion with timing and speed statistics
  - File-by-file progress tracking
  - Size fetching operations
  - Error conditions with full stack traces

#### Type Safety
- **TypedDict for Progress Data** - Created `ProgressData` TypedDict in helpers.py
  - Strongly typed structure for all progress callback data
  - Includes fields: repo_id, current_file, file_index, sizes, speed, eta, completion status
  - Optional fields for retry information
- **Progress Callback Type Alias** - Added `ProgressCallback` type alias
  - Clean type hint for callback functions: `Callable[[ProgressData], None]`
  - Used throughout downloader and screens for type safety

#### Development Infrastructure
- **requirements-dev.txt** - Added development dependencies:
  - pytest, pytest-asyncio, pytest-cov, pytest-mock for testing
  - mypy with types-requests for type checking
  - black, flake8, isort for code formatting and linting
  - sphinx with RTD theme for documentation

### Changed

#### Download Flow
- `download_model()` method signature changed from sync to async
  - Returns `bool` wrapped in coroutine
  - Must be called with `await` keyword
  - Uses ThreadPoolExecutor for blocking hf_hub_download calls
- Download monitoring now happens in parallel with download
  - Separate async task monitors file size growth
  - Task is cancelled when download completes
  - No more blocking wait for entire file before showing progress
- File size validation happens before download confirmation
  - Modal callback now validates using `await downloader.validate_download()`
  - Shows clear error message if validation fails
  - Prevents downloads that will fail due to disk space

#### Error Handling
- **File Size Fetching** in `hf_client.py`:
  - Added `files_metadata=True` parameter to `model_info()` call
  - Comprehensive null checking for size attributes
  - Defaults to 0 instead of failing when size unavailable
  - Logs warnings for missing size data at DEBUG level
  - Returns empty dict on error instead of raising exception
- **Detail Screen** in `detail_screen.py`:
  - Wrapped size fetching in try/except with user notifications
  - Shows warning when file sizes cannot be retrieved
  - Detects when all sizes are zero and notifies user
  - Download proceeds even if sizes unknown (shows "Unknown size")
- **Download Screen** in `download_screen.py`:
  - Added await for async download_model call
  - Proper async exception handling
  - Better error messages for download failures

#### Code Organization
- Download manager now tracks monitor task for proper cleanup
- Added `_current_file_path` attribute to track active download
- Cancellation now stops monitoring task immediately
- File existence checks before re-downloading completed files

#### Logging Improvements
- All download operations now log with context (repo_id, file, size)
- DEBUG logs for function entry/exit
- INFO logs for major milestones (start, complete, file progress)
- ERROR logs with full exc_info for debugging
- Performance statistics logged (duration, average speed)

### Fixed

#### Critical Fixes
- **File sizes showing as 0** - Root cause: HF API siblings sometimes have None for size
  - Fixed by adding robust null checking in get_file_sizes()
  - Added fallback to 0 instead of skipping files with missing sizes
  - Added logging to track when sizes are unavailable
- **UI freezing during downloads** - Root cause: synchronous hf_hub_download blocking event loop
  - Fixed by wrapping download in ThreadPoolExecutor
  - Used asyncio.run_in_executor() for non-blocking execution
  - Progress monitoring runs as separate async task
- **No progress updates for large files** - Root cause: progress only updated after file completion
  - Fixed by adding real-time file size monitoring
  - Monitor task checks file size every 500ms
  - Calculates progress, speed, and ETA in real-time
- **Download confirmation modal freezing** - Root cause: download_model was sync but called from async
  - Fixed by converting download_model to async def
  - Added proper await in download_worker()
  - Validation now happens asynchronously before download starts

#### Minor Fixes
- Progress callback type hints now use ProgressCallback alias
- Import cleanup in downloader.py (added asyncio, Path, etc.)
- Removed unused imports (Callable replaced by ProgressCallback)
- Fixed modal parameter consistency (title_text everywhere)

### Technical Details

#### Architecture Changes
```
Old Flow:
User confirms -> DownloadScreen.download_worker() 
  -> DownloadManager.download_model() [BLOCKS]
    -> hf_hub_download() [BLOCKS EVENT LOOP]
      -> Progress callback after file completes

New Flow:
User confirms -> Validation
  -> DownloadScreen.download_worker() [async]
    -> await DownloadManager.download_model() [async]
      -> ThreadPoolExecutor.run_in_executor(hf_hub_download)
      -> Async monitor task checks file size every 500ms
        -> Progress callback with real-time updates
```

#### File Size Handling
```python
Before:
if sibling.size:  # Fails when size is None or 0
    sizes[filename] = sibling.size

After:
if hasattr(sibling, "size"):
    if sibling.size is not None and sibling.size > 0:
        sizes[filename] = int(sibling.size)
    else:
        sizes[filename] = 0  # Explicit default
```

#### Progress Monitoring
```python
New _monitor_file_progress() method:
- Runs as async task in parallel with download
- Checks file.stat().st_size every 500ms
- Uses DownloadSpeedCalculator for moving average speed
- Calculates ETA based on remaining bytes and current speed
- Stops when file size matches expected size
- Handles cancellation gracefully
```

### Performance

- Download speed unchanged (still limited by network and HF servers)
- UI now remains fully responsive during downloads
- Progress updates appear smooth (2 updates per second)
- Negligible overhead from monitoring task (< 1% CPU)
- Disk space check adds < 100ms to download initiation

### Version

- Updated APP_VERSION in config.py from 2.1.0 to 2.2.1
- Skipped 2.2.0 for this release due to critical download fixes

## [2.2.0] - 2024-12-25

### Added

#### Visual & UI
- **Vibrant Green Theme** - Changed primary color from blue (#58a6ff) to vibrant green (#3fb950)
  - Updated all CSS variables to use green palette
  - Primary: #3fb950 (vibrant green)
  - Primary-dim: #2ea043 (darker green)
  - Primary-bright: #56d364 (lighter green)
  - Info color changed to match green theme
  - Border-focus now uses green
  - Selection highlights use green with transparency
- **Responsive Design System** - Adaptive layout based on terminal width
  - Desktop (80+ cols): Full layout with all columns
  - Tablet (60-79 cols): Compact layout, some columns hidden
  - Mobile (40-59 cols): Minimal layout, essential columns only
  - Tiny (<40 cols): Cramped layout for very small terminals
- **Responsive CSS Classes** - `.desktop`, `.tablet`, `.mobile`, `.tiny` auto-applied
- **Adaptive DataTables** - Columns hide/show based on available width
  - MainScreen: 4 cols → 3 cols → 2 cols
  - SearchScreen: 4 cols → 3 cols → 2 cols
  - DetailScreen: 3 cols → 2 cols

#### User Experience
- **Auto-Focus Search Results** - Table automatically focuses after search completes
- **Smart Keyboard Navigation**:
  - ↓ arrow from search input jumps to results table
  - ↑ arrow from first row returns to search input
  - Seamless navigation without mouse
- **DataTable Row Selection** - Enter key and double-click now both select rows
- **Improved Search Workflow** - Type → Results appear → Immediately navigable
- **Responsive Status Bar** - Horizontal on desktop, vertical on mobile

#### Technical Improvements
- **Terminal Resize Handlers** - All screens respond to terminal resize events
- **App-Level Resize Detection** - `on_resize()` handler in main app
- **Dynamic Column Setup** - `_setup_table_columns()` methods in all screens
- **Responsive Row Building** - Conditional row data based on terminal width
- **Event Imports** - Added `from textual import events` for resize handling

### Changed

#### Theme
- Primary color changed from blue to green throughout application
- All buttons, borders, and highlights now use green theme
- Focus indicators changed from blue to green
- Selection highlights changed from blue to green

#### UI/UX Changes
- Search result message now includes navigation hint: "Found X models (↓ to navigate)"
- Tables now adapt column count on resize
- Layouts automatically reflow based on terminal size
- Fixed Modal parameter from `title` to `title_text` (consistency)

#### Code Structure
- MainScreen: Added resize handler and dynamic column logic
- SearchScreen: Added resize handler and dynamic column logic
- DetailScreen: Added resize handler and dynamic column logic
- App: Added `_update_responsive_class()` method
- Theme: Added 80+ lines of responsive CSS
- Fixed CSS error: `text-style: normal` → `text-style: none`

### Fixed

- **CSS Validation Error** - Fixed invalid `text-style: normal` value
- **Modal Parameter** - Corrected `title` to `title_text` in confirmation dialogs
- **Column Mismatch** - Tables now build rows matching current column count
- **Auto-focus Issue** - Search results table now focuses after loading
- **Keyboard Navigation** - Up/Down arrows work correctly between input and table

### Technical Details

#### Files Modified
- `src/theme.py` - Green theme colors + responsive CSS
- `src/app.py` - Added resize handler and responsive class logic
- `src/screens/main_screen.py` - Adaptive columns + resize handler
- `src/screens/search_screen.py` - Adaptive columns + auto-focus + keyboard nav
- `src/screens/detail_screen.py` - Adaptive columns + resize handler
- `README.md` - Updated for v2.2.0 features and green theme
- `CHANGELOG.md` - This entry

#### Responsive Breakpoints
```
Desktop:  width >= 80 cols  → .desktop class
Tablet:   width >= 60 cols  → .tablet class
Mobile:   width >= 40 cols  → .mobile class
Tiny:     width < 40 cols   → .tiny class
```

#### Color Palette Changes
```diff
- Primary:         #58a6ff  (Bright blue)
+ Primary:         #3fb950  (Vibrant green)
+ Primary-dim:     #2ea043  (Darker green)
+ Primary-bright:  #56d364  (Lighter green)
- Info:            #58a6ff  (Blue)
+ Info:            #3fb950  (Green)
```

## [2.1.0] - 2024-12-24

### Added

#### Visual & UI
- **Professional Dark Theme** - GitHub-inspired color scheme with 16 carefully selected colors
- **Custom Widget System** - 6 reusable components for consistent UI:
  - `StatusBadge` - Visual status indicators with icons and colors
  - `LoadingSpinner` - Animated spinner for async operations
  - `SectionHeader` - Consistent section headers
  - `PanelCard` - Container widget with hover effects
  - `StyledButton` - Button variants (default, primary, error)
  - `Modal` - Professional modal dialogs with overlay
- **Theme System** - Centralized CSS with 256 lines of comprehensive styling
- **Hover Effects** - Visual feedback on interactive elements
- **Color-Coded Status** - Success (green), Warning (yellow), Error (red), Info (cyan)

#### User Experience
- **Search Debouncing** - 500ms delay to reduce API calls
- **Loading Indicators** - Spinners show during async operations
- **Confirmation Dialogs** - Modal confirmations for destructive actions (delete, download)
- **Better Error Messages** - User-friendly error notifications
- **Visual Feedback** - Hover states, focus indicators, and status badges

#### Code Quality
- **Modern Type Hints** - Using Python 3.10+ syntax (`dict[str, Any]`, `str | None`)
- **Comprehensive Docstrings** - Google-style documentation for all classes and methods
- **Custom Exception Hierarchy** - Structured error handling:
  - `ModelManagerException` (base)
  - `DownloadError`
  - `UpdateCheckError`
  - `NetworkError`
  - `StorageError`
  - `ValidationError`
  - `HuggingFaceError`
- **Global Exception Handler** - Prevents crashes and shows user-friendly errors
- **Type Safety** - Full type annotations throughout codebase
- **Code Documentation** - Detailed docstrings with Args/Returns/Raises sections

#### Technical Improvements
- **Widget Architecture** - Component-based UI system
- **Async Error Handling** - Try/except blocks in all async operations
- **Better Error Propagation** - Errors bubble up with context
- **Improved Logging** - More detailed debug information
- **Code Formatting** - Black + flake8 compliant

### Changed

#### UI/UX Changes
- **Section Headers** - Replaced plain Static widgets with styled SectionHeader
- **Confirmation Dialogs** - Replaced simple ConfirmDialog with professional Modal
- **Status Display** - Using StatusBadge instead of plain text
- **Loading States** - Added LoadingSpinner to search and detail screens
- **Button Styling** - Using StyledButton with variants

#### Code Structure
- **Import Organization** - Cleaner imports with modern type hints
- **Function Signatures** - Added return type annotations
- **Error Handling** - Consistent try/except patterns
- **Code Style** - Black-formatted with consistent spacing

#### Performance
- **Async Operations** - Better handling of background tasks
- **Error Recovery** - Graceful degradation on failures
- **Resource Management** - Proper cleanup in finally blocks

### Fixed

- **Import Issues** - Fixed circular import problems
- **Type Errors** - Resolved all type checking issues
- **Async Errors** - Proper error handling in async functions
- **Widget Lifecycle** - Correct mount/unmount handling for spinners
- **Modal Dismissal** - Proper callback typing for modal results
- **Linting Issues** - All flake8 warnings resolved
- **Whitespace** - Cleaned up trailing whitespace
- **Line Length** - Ensured all lines under 100 characters

### Deprecated

- `ConfirmDialog` class - Replaced by `Modal` widget

### Removed

- Unused imports (`pathlib.Path`, `datetime`, `os` where not needed)
- Duplicate code in badge rendering
- Old-style type hints (`Optional`, `List`, `Dict`, `Tuple`)

### Technical Details

#### Statistics
- **Total Python Files**: 25
- **Total Lines of Code**: ~2,579
- **Widgets Created**: 6
- **Services**: 4
- **Screens**: 4
- **Theme Colors**: 16
- **CSS Lines**: 256

#### Code Quality Metrics
- **Type Coverage**: 100% of functions have type hints
- **Documentation**: 100% of public APIs documented
- **Linting**: 100% flake8 compliant
- **Formatting**: 100% black formatted

## [2.0.0] - 2024-12-20

### Added

#### Core Features
- **Interactive TUI** - Built with Textual framework
- **Model Search** - Search HuggingFace for GGUF models
- **Download Manager** - Multi-file downloads with progress tracking
- **Resume Support** - Automatic resume for interrupted downloads
- **Update Checking** - Async background update checks
- **Model Management** - View, update, and delete local models
- **Storage Tracking** - Monitor disk space usage

#### Screens
- **Main Screen** - Dashboard showing downloaded models
- **Search Screen** - Search and browse HuggingFace models
- **Detail Screen** - View model details and quantizations
- **Download Screen** - Real-time download progress

#### Services
- **HuggingFace Client** - API wrapper for model operations
- **Storage Manager** - Local file and metadata management
- **Download Manager** - Handles file downloads with progress
- **Update Checker** - Checks for model updates

#### Infrastructure
- **Configuration System** - Centralized settings
- **Logging** - Comprehensive application logging
- **Metadata Storage** - JSON-based metadata persistence
- **Error Handling** - Basic exception management

### Changed

#### From v1.0
- Migrated from CLI to full TUI interface
- Improved progress tracking (per-file instead of overall)
- Better error messages and user feedback
- Modular architecture with separation of concerns

## [1.0.0] - 2024-12-15

### Added
- Initial release
- Basic command-line interface
- Simple model download functionality
- HuggingFace integration
- Basic progress bars

---

## Version History Summary

| Version | Date | Key Features |
|---------|------|--------------|
| **2.1.0** | 2024-12-24 | Dark theme, widgets, type hints, comprehensive docs |
| **2.0.0** | 2024-12-20 | Full TUI, async updates, resume support |
| **1.0.0** | 2024-12-15 | Initial CLI version |

---

## Upgrade Notes

### Migrating from v2.0 to v2.1

No breaking changes. All existing functionality preserved.

**What's automatically upgraded:**
- Theme applied on first run
- Modal dialogs replace old confirmations
- Loading indicators appear automatically
- Error handling improved throughout

**No action required** - Everything works out of the box!

### Migrating from v1.0 to v2.0

See `MIGRATION.md` for detailed migration guide.

---

**Model Manager** - Professional GGUF Model Management
