# Model Manager v2.2.1

A modern Terminal User Interface (TUI) for managing GGUF models from HuggingFace with a vibrant green theme, responsive design, and enhanced user experience.

## Features

- **Vibrant Green Theme** - Eye-friendly green color scheme with 16 carefully selected colors
- **Responsive Design** - Adaptive layout for desktop (80+ cols), tablet (60-79 cols), and mobile (<60 cols)
- **Modern Widget System** - Reusable components including StatusBadge, LoadingSpinner, Modal, and more
- **Enhanced Search** - Auto-focus results, smart keyboard navigation (up/down arrows), and debounced input
- **Real-Time Download Progress** - Byte-level progress tracking with live speed and ETA updates
- **Async Download System** - Non-blocking downloads with progress monitoring using ThreadPoolExecutor
- **Pre-Download Validation** - Automatic disk space and file validation before downloads begin
- **Async Update Checking** - Non-blocking background checks for model updates
- **Model Management** - View, update, and delete downloaded models with confirmation dialogs
- **Storage Tracking** - Monitor disk space usage in real-time
- **Robust Error Handling** - Comprehensive error handling with user-friendly error messages and warnings

## 🚀 Installation

### Requirements

- Python 3.10+ (for modern type hints)
- pip

### Install Dependencies

```bash
pip install -r requirements.txt
```

## 📖 Usage

### Run the Application

```bash
python3 run.py
```

Or make it executable:

```bash
chmod +x run.py
./run.py
```

### ⌨️ Keyboard Shortcuts

**Main Screen:**
- `S` - Search for models
- `R` - Refresh model list and check for updates
- `Enter` - View model details
- `D` - Delete selected model (with confirmation)
- `U` - Update selected model
- `Q` - Quit application

**Search Screen:**
- Type to search (with 500ms debounce)
- `↓` - Jump from search to results table
- `↑` - Return to search from first result
- `Enter` - View model details (or double-click row)
- `Esc` / `Q` - Go back

**Detail Screen:**
- `D` - Download selected quantization (with confirmation)
- `Esc` / `Q` - Go back

**Download Screen:**
- `C` / `Esc` - Cancel download

## 🎨 UI Components

### Widgets

1. **StatusBadge** - Visual status indicators
   - ✓ Success (green)
   - ⬆ Warning/Update (yellow)
   - ✗ Error (red)
   - ℹ Info (cyan)
   - ◌ Checking (cyan)

2. **LoadingSpinner** - Animated spinner (◐ ◓ ◑ ◒)
   - Indicates background operations
   - Auto-animates at 0.5s intervals

3. **SectionHeader** - Consistent section titles
   - Styled with primary color
   - Optional icon support

4. **Modal** - Professional confirmation dialogs
   - Semi-transparent overlay
   - Yes/No options
   - Keyboard navigation

5. **StyledButton** - Button variants
   - Default, Primary, Error styles
   - Hover effects

6. **PanelCard** - Container widget
   - Consistent borders and padding
   - Hover state styling

### Theme Colors

```
Background:      #0d1117  (Deep dark)
Surface:         #161b22  (Slightly lighter)
Primary:         #3fb950  (Vibrant green) ✨ NEW in v2.2.0
Primary-dim:     #2ea043  (Darker green)
Primary-bright:  #56d364  (Lighter green)
Accent:          #a371f7  (Purple)
Success:         #3fb950  (Green)
Warning:         #d29922  (Orange)
Error:           #f85149  (Red)
```

## 📁 Project Structure

```
model-manager/
├── run.py                      # Entry point
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── CHANGELOG.md                # Version history
├── src/
│   ├── app.py                  # Main application (142 lines)
│   ├── config.py               # Configuration
│   ├── theme.py                # Dark theme CSS (267 lines)
│   ├── exceptions.py           # Custom exceptions
│   ├── models.py               # Data models
│   │
│   ├── widgets/                # Reusable UI components (6 widgets)
│   │   ├── status_badge.py     # Status indicators
│   │   ├── loading.py          # Loading spinner
│   │   ├── section_header.py   # Section headers
│   │   ├── card.py             # Panel containers
│   │   ├── styled_button.py    # Styled buttons
│   │   └── modal.py            # Modal dialogs
│   │
│   ├── services/               # Backend services
│   │   ├── hf_client.py        # HuggingFace API wrapper
│   │   ├── storage.py          # Local storage management
│   │   ├── downloader.py       # Download manager
│   │   └── updater.py          # Update checker
│   │
│   ├── screens/                # TUI screens
│   │   ├── main_screen.py      # Dashboard with model list
│   │   ├── search_screen.py    # Search interface
│   │   ├── detail_screen.py    # Model details & quantizations
│   │   └── download_screen.py  # Download progress
│   │
│   └── utils/
│       └── helpers.py          # Utility functions
│
└── models/                     # Downloaded models (created on first run)
    └── .metadata.json          # Model metadata
```

## 🎯 How It Works

### Search & Download

1. Press `S` to open search screen
2. Type keywords (e.g., "llama", "mistral", "phi")
3. Watch the loading spinner while searching
4. Navigate results with arrow keys
5. Press `Enter` to view model details
6. Select a quantization and press `D`
7. Confirm download in modal dialog
8. Monitor real-time progress with speed and ETA
9. Download resumes automatically if interrupted

### Update Checking

The app performs async update checks in the background:

- **On Startup**: Checks all local models for updates
- **Manual Refresh**: Press `R` to trigger update check
- **Status Indicators**: Visual badges show update status

Update statuses:
- **Up to date** ✓ - Model is current
- **Update available** ⬆ - Newer version exists  
- **Checking...** ◌ - Update check in progress
- **Error** ✗ - Check failed
- **Unknown** - No information available

### Model Organization

Models are stored with this structure:

```
models/
├── author-name/
│   └── model-name/
│       ├── model-q4_0.gguf
│       ├── model-q4_1.gguf
│       └── model-q5_0.gguf
└── .metadata.json              # Stores download dates and commit SHAs
```

## What's New in v2.2.1

### Download System Overhaul
- **Async Download Architecture** - Complete rewrite using ThreadPoolExecutor for non-blocking downloads
- **Real-Time Progress Monitoring** - Byte-level progress tracking with 500ms update intervals
- **File Size Validation** - Robust file size fetching with comprehensive error handling
- **Pre-Download Validation** - Automatic disk space checking and repository validation
- **Improved Cancellation** - More responsive download cancellation with proper cleanup
- **Enhanced Logging** - Comprehensive debug logging throughout download flow

### Type Safety and Code Quality
- **TypedDict for Progress Data** - Strongly typed progress callback structure
- **Progress Callback Type Alias** - Clean type hints for callback functions
- **Improved Error Messages** - User-friendly warnings when file sizes unavailable
- **Development Dependencies** - Added pytest, mypy, black, and flake8 for testing

### Bug Fixes
- Fixed file sizes showing as 0 in quantization listings
- Fixed UI freezing during model downloads
- Fixed missing progress updates for large files
- Fixed download modal not appearing after confirmation
- Added proper async/await throughout download flow

## What's New in v2.2.0

### Visual Improvements
- **Vibrant green theme** - Changed from blue to eye-friendly green (#3fb950)
- **Responsive layout** - Adaptive UI for different terminal widths
- **Auto-hiding columns** - Desktop (4 cols) to Tablet (3 cols) to Mobile (2 cols)
- All CSS variables updated to green palette

### User Experience Enhancements
- **Auto-focus on search results** - Results table focuses immediately after search
- **Smart keyboard navigation** - Down arrow jumps to results, up arrow returns to search
- **Row selection events** - Press Enter or double-click to select
- **Responsive breakpoints**:
  - Desktop: 80+ columns (full layout)
  - Tablet: 60-79 columns (compact)
  - Mobile: 40-59 columns (minimal)
  - Tiny: <40 columns (cramped)

### Technical Improvements
- Terminal resize handlers in all screens
- Dynamic column setup based on width
- Responsive CSS classes (`.desktop`, `.tablet`, `.mobile`, `.tiny`)
- App-level resize detection
- Adaptive row building for DataTables

## Version History

### v2.2.1 (Current)
- Async download system with ThreadPoolExecutor
- Real-time byte-level progress monitoring
- Pre-download validation (disk space, file sizes)
- Robust error handling for file size fetching
- TypedDict for type-safe progress callbacks
- Comprehensive logging throughout download flow
- Fixed UI freezing issues during downloads
- Fixed file sizes showing as zero

### v2.2.0
- Green theme conversion
- Responsive design system
- Enhanced search UX
- Smart keyboard navigation

### v2.1.0
- Professional dark theme
- Custom widget system
- Async update checking
- Modal dialogs

## 🔧 Troubleshooting

### Import Errors

Ensure you're running from the project root:

```bash
cd /path/to/model-manager
python3 run.py
```

### Python Version

Requires Python 3.10+ for modern type hints:

```bash
python3 --version  # Should show 3.10 or higher
```

### Download Issues

1. Check `model_manager.log` for errors
2. Verify internet connection
3. Ensure sufficient disk space
4. Try resuming (downloads auto-resume)

### Terminal Size

**Responsive Breakpoints:**
- Desktop (80+ cols): Full layout with all columns
- Tablet (60-79 cols): Compact layout, some columns hidden
- Mobile (40-59 cols): Minimal layout, essential columns only
- Tiny (<40 cols): Cramped layout, may have visual issues

**Recommended:**
- Minimum: 60x24 for good experience
- Optimal: 100x30 or larger
- The app adapts automatically when you resize your terminal!

### Theme Not Showing

If colors look wrong:
- Use a terminal with 256-color support
- Try a modern terminal (iTerm2, Alacritty, Windows Terminal)
- Check terminal theme compatibility

## 📊 Statistics

- **Total Files**: 25 Python files
- **Total Code**: ~2,579 lines
- **Widgets**: 6 reusable components
- **Screens**: 4 fully-featured screens
- **Services**: 4 backend services
- **Theme Colors**: 16 carefully selected
- **CSS Lines**: 256 lines of styling

## 🧪 Development

### Code Style

```bash
# Format code
black src/

# Check linting
flake8 --max-line-length=100 src/

# Type checking (if mypy installed)
mypy src/
```

### Testing

Run the app in test mode:

```bash
python3 -c "from src.app import run; run()"
```

## 📝 Logs

Application logs: `model_manager.log` in project directory

Log levels:
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Failures and exceptions

## 🤝 Contributing

This is a personal project, but suggestions are welcome via issues.

## 📄 License

This project is provided as-is for personal use.

## 🙏 Acknowledgments

- Built with [Textual](https://textual.textualize.io/) - Modern TUI framework
- Uses [HuggingFace Hub](https://huggingface.co/) - Model repository
- Theme inspired by GitHub's dark mode

---

**Model Manager v2.2.0** - A responsive TUI for GGUF model management with vibrant green theme
