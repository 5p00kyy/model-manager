# Changelog

All notable changes to Model Manager will be documented in this file.

## [2.5.1] - 2025-12-27

### 🔧 Critical Bug Fixes

#### UnboundLocalError on Download Start (CRITICAL)
- **✅ Fixed crash when starting downloads** - Variable `overall_downloaded` referenced before assignment
- **✅ Bug occurred in heartbeat code path** - When file size didn't change but heartbeat triggered (≥0.5s)
- **✅ Root cause:** Variable only defined inside `if size_changed:` block, but used in `elif` heartbeat block
- **✅ Solution:** Calculate `overall_downloaded` BEFORE conditional blocks using new helper method

### ✨ Code Quality Improvements

**Constants Added:**
- `PROGRESS_HEARTBEAT_INTERVAL = 0.5` - How often to send heartbeat updates
- `PROGRESS_POLL_INTERVAL = 0.1` - How often to check file size
- `SPEED_CALC_WINDOW_SIZE = 10` - Moving window size for speed calculation

**New Helper Method:**
- `_calculate_overall_downloaded()` - Encapsulates progress calculation logic
- Returns tuple of (overall_downloaded, new_bytes_this_session)
- Properly handles resumed downloads without double-counting bytes

**Enhanced Documentation:**
- Added comprehensive docstring for `_download_with_progress()`
- Documents key features, calculation logic, monitoring strategy
- Explains all parameters and edge cases

**Error Handling:**
- Added permission error handling for cache directory access
- Graceful fallback when local/global cache is inaccessible

### 🧪 Test Coverage

**Added 5 New Test Cases (21 total, all passing):**
1. `test_heartbeat_progress_when_size_unchanged` - Tests the UnboundLocalError fix
2. `test_resumed_download_calculation_accuracy` - Validates resume math (1GB + 500MB ≠ 2.5GB)
3. `test_calculate_overall_downloaded_multiple_files` - Tests multi-file progress
4. `test_download_monitoring_before_file_appears` - Tests file not found initially
5. `test_calculate_overall_downloaded_edge_cases` - Tests boundary conditions

**Test Results:**
- 21/21 tests passing ✅
- 0 failures ✅
- Test duration: 0.27s ✅

### 📊 Code Quality Metrics

- **Black formatting:** ✅ All files compliant (100 char line length)
- **Flake8 linting:** ✅ Zero issues
- **Type hints:** ✅ All functions properly typed
- **Test coverage:** ✅ All critical paths covered

---

## [2.5.0] - 2025-12-26

### 🎯 Critical Progress Display Fixes

#### Resumed Download Accuracy (CRITICAL BUG FIX)
- **✅ Fixed "83% complete immediately on resume" bug** - Was counting incomplete file bytes as "downloaded" from previous session
- **✅ Track initial incomplete file size** - Records starting bytes before monitoring begins
- **✅ Only count NEW bytes this session** - Progress increases correctly from resumed percentage
- **✅ Smart monitoring source selection** - Uses most recently modified file (local vs global cache)
- **✅ Seed speed calculator with initial bytes** - Prevents erratic speed spikes on resumed downloads

#### Visual Improvements
- **✅ Prominent progress percentage** - Now shows "8.5 GB / 10.2 GB (83%) - (1/3 files)"
- **✅ Resumed download indicator** - Status shows "Resuming download... (8.9 GB already downloaded)"
- **✅ Color-coded speed display** - Green (>10 MB/s), Cyan (>1 MB/s), Yellow (>100 KB/s), Red (slow/stalled)
- **✅ Improved speed calculation** - Uses last half of window for current speed, falls back to full window if stalled
- **✅ Zero-delta filtering** - Speed calculator skips samples with no byte changes to prevent 0 speed

### Technical Implementation

**DownloadManager (`src/services/downloader.py`):**
- Track `initial_incomplete_size` before monitoring starts
- Calculate `new_bytes_this_session = current_size - initial_incomplete_size`
- Overall progress: `initial_bytes + new_bytes_this_session` (not just `current_size`)
- Collect monitoring candidates from all sources and use most recently modified
- Add `_is_resuming` and `_initial_bytes_before` instance variables
- Seed speed calculator with initial bytes before monitoring begins

**DownloadSpeedCalculator (`src/utils/helpers.py`):**
- Use last half of window for current speed (more responsive)
- Filter zero-delta samples to prevent 0 speed from stalls
- Fall back to full window if recent samples show no progress

**DownloadScreen (`src/screens/download_screen.py`):**
- Show overall percentage prominently: "8.5 GB / 10.2 GB (83%)"
- Display status based on `progress_data["status"]` field
- Color-code speed: Green, Cyan, Yellow, Red based on performance
- Handle "resuming", "downloading", "finalizing" status types

**Testing:**
- Added `test_progress_data_resumed_download()` to verify resumed download detection
- All 16 tests passing (100% pass rate)
- Verified color-coded speed display logic

### Impact

**Before (v2.4.0):**
```
Status: Downloading...
Progress: 8.9 GB / 10.2 GB (87%)  ← WRONG! Shows 87% immediately on resume
Speed: 0 B/s  ← WRONG! Shows 0 or erratic values
ETA: Unknown  ← WRONG! Can't calculate from erratic speed
```

**After (v2.5.0):**
```
Status: Resuming download... (8.9 GB already downloaded)  ✓ CLEAR
Progress: 8.9 GB / 10.2 GB (87%) - 45.2 MB/s  ✓ ACCURATE
Speed: [green]45.2 MB/s[/]  ✓ COLOR-CODED
ETA: 1m 23s  ✓ ACCURATE
```

### User Experience Improvements
1. **Resumed downloads work correctly** - Progress starts at correct percentage and increases
2. **Accurate speed tracking** - Real-time speed without erratic spikes
3. **Visual clarity** - Prominent percentage, color-coded speed, clear status
4. **Robust monitoring** - Always tracks the most recent file, regardless of cache location

## [2.4.0] - 2025-12-26

### 🚀 Major Navigation & Progress Improvements

#### Download Progress Accuracy
- **✅ Real-Time Speed Tracking** - Implemented moving window average for accurate current download speed
- **✅ Smart ETA Display** - ETA now based on current speed, not average from start
- **✅ Stall Detection** - Shows "Download stalled" when speed drops below 1 KB/s for 5+ seconds
- **✅ Accurate File Count** - Displays "0/3 → 1/3 → 2/3 → 3/3" based on files actually completed
- **✅ Eliminated Stale Updates** - Progress only updates when bytes actually increase

#### Seamless Navigation Flow
- **✅ Auto-Focus Quantization Table** - Table auto-focuses after loading (no Tab required!)
- **✅ Enter Key Downloads** - Press Enter on any quantization to start download immediately
- **✅ Smart Arrow Navigation** - Arrow keys intelligently switch between buttons and table
- **✅ Improved Button Labels** - "Download Selected" clarifies which quantization will download
- **✅ Consistent UX** - Navigation flow matches search screen behavior

### Technical Implementation

**Download Progress (`src/services/downloader.py`):**
- Integrated `DownloadSpeedCalculator` with 10-sample moving window (~3 second average)
- Added stale update detection using `last_reported_size` tracking
- Speed calculator only updates on actual byte changes, not duplicate values
- Improved `_send_progress()` to use `calculate_eta()` helper function

**Download UI (`src/screens/download_screen.py`):**
- Fixed file count calculation to show completed files accurately
- Enhanced ETA display with stall detection (< 1 KB/s after 5 seconds)
- Added intelligent status messages: "Calculating...", "Download stalled", "Unknown"
- Eliminated duplicate `file_pct` calculation

**Detail Screen (`src/screens/detail_screen.py`):**
- Added `_focus_quant_table()` method called after quantizations load
- Implemented `on_data_table_row_selected()` for Enter key support
- Added `on_key()` handler for smart arrow navigation between widgets
- Updated button label to "Download Selected" for clarity

### Testing & Quality

**New Tests:**
- `test_speed_calculator_initialization()` - Verifies DownloadSpeedCalculator setup
- `test_speed_calculator_multiple_samples()` - Tests moving window averaging
- `test_speed_calculator_window_size()` - Confirms window size limits
- `test_speed_calculator_reset()` - Validates reset functionality
- `test_eta_calculation_zero_speed()` - Tests zero speed edge case
- `test_navigation.py` - Integration test for navigation improvements

**Test Results:**
- 15/15 unit tests pass
- All navigation tests pass
- Code formatted with black (100 char lines)

### User Experience Improvements

**Before:**
- Speed: Shows average from start (inaccurate, sluggish)
- ETA: Based on average speed (wildly inaccurate)
- File count: Shows "1/1" when downloading first file
- Navigation: Required Tab to focus table, Tab to button, then Enter
- Stalls: Speed slowly drifts down over time

**After:**
- Speed: Real-time moving average (accurate, responsive)
- ETA: Based on current conditions (much more accurate)
- File count: Shows "0/3" while downloading first file (intuitive)
- Navigation: Table auto-focuses, Enter downloads (2 steps instead of 5!)
- Stalls: Shows "Download stalled" immediately when detected

## [2.3.0] - 2025-12-26

### 🎉 Major Improvements

#### Download System Overhaul
- **✅ FIXED: Download progress now updates in real-time** - No more stuck at "Preparing download... 0%"!
- **Byte-level Progress Monitoring** - See actual download progress every 300ms during large file downloads
- **Retry Logic** - Automatic retry (up to 3 attempts) for transient network failures with exponential backoff
- **Better Error Handling** - Comprehensive error messages and proper exception handling throughout
- **UI Lifecycle Guards** - Fixed crashes when screen is unmounted during download

#### UI/UX Enhancements
- **Elapsed Time Display** - See how long the download has been running
- **Improved Progress Metrics** - More accurate speed and ETA calculations
- **Lifecycle Safety** - Widgets properly guarded against updates after unmount
- **Better Status Messages** - Clear indication of what's happening during download

### Code Quality
- **Code Formatting** - All code formatted with black (line length: 100)
- **Linting** - Fixed linting issues, clean code style
- **Unit Tests** - Comprehensive test suite for download manager (9 tests, 100% pass rate)
- **Type Safety** - Proper TypedDict usage for progress data structures

### Technical Details

**Files Changed:**
- `src/services/downloader.py` - Complete rewrite of progress monitoring system
- `src/screens/download_screen.py` - Added lifecycle guards and elapsed time display
- `tests/test_downloader.py` - New comprehensive test suite

**New Features:**
1. **Byte-Level Progress Monitoring**
   - Monitors HuggingFace cache directory for file growth
   - Updates UI every 300ms with actual bytes downloaded
   - Calculates real-time speed and ETA

2. **Retry System**
   - 3 automatic retries for failed downloads
   - Exponential backoff (2, 4, 8 seconds)
   - Proper error logging and user notifications

3. **Lifecycle Management**
   - `_is_mounted` flag prevents updates to unmounted screens
   - Proper cleanup on screen unmount
   - Safe widget access with try/except guards

### Bug Fixes
- Fixed "NoMatches" error when updating unmounted download screen
- Fixed download progress stuck at 0% for large files
- Fixed UI freezing during downloads
- Fixed missing progress updates during file download
- Fixed cancellation not properly cleaning up resources

---

## [2.2.1] - 2025-12-25

### Download System
- Async download architecture with ThreadPoolExecutor
- Real-time progress monitoring attempt
- File size validation
- Pre-download validation

### Bug Fixes
- Fixed file sizes showing as 0
- Attempted to fix UI freezing during downloads

---

## [2.2.0] - 2025-12-24

### Visual Improvements
- Vibrant green theme
- Responsive layout

### UX Enhancements
- Auto-focus on search results
- Smart keyboard navigation

---

## [2.1.0] - Initial modular release

### Features
- Professional dark theme
- Custom widget system
- Async update checking
