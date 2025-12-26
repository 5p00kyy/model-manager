# Changelog

All notable changes to Model Manager will be documented in this file.

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
