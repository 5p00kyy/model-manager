# Changelog

All notable changes to Model Manager will be documented in this file.

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
