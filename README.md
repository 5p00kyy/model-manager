# Model Manager

A modern Terminal User Interface (TUI) for managing GGUF models from HuggingFace. Features real-time download progress, accurate progress tracking, seamless navigation, and a vibrant dark theme.

## Features

### Download Management

- **Real-Time Progress Tracking** - Monitor downloads byte-by-byte with accurate speed and ETA
- **Resumed Download Support** - Automatically resume interrupted downloads from where they left off
- **Intelligent Speed Calculation** - Moving window average provides accurate current download rates
- **Automatic Retry** - Network failures automatically retry with exponential backoff
- **Color-Coded Status** - Visual feedback with green (fast), cyan (good), yellow (slow), red (stalled)
- **Stall Detection** - Immediate feedback when download speed drops below threshold

### User Interface

- **Vibrant Dark Theme** - Eye-friendly color scheme optimized for terminal viewing
- **Responsive Design** - Adaptive layout for desktop (80+ cols), tablet (60-79 cols), and mobile (<60 cols)
- **Smart Navigation** - Auto-focus, Enter key actions, intelligent arrow key movement
- **Seamless Flow** - No excessive Tab key presses needed
- **Modern Widgets** - Reusable components with consistent styling
- **Confirmation Modals** - Clear dialogs for destructive actions

### Model Management

- **Search & Browse** - Find models on HuggingFace with debounced search
- **View Details** - Complete model information with available quantizations
- **Download** - Select specific quantizations with clear file size information
- **Update Checking** - Automatic background checks for model updates
- **Update Status** - Visual badges showing up-to-date or update available
- **Delete Models** - Remove local models with confirmation

## Installation

### Requirements

- Python 3.10 or higher
- pip package manager

### Install

```bash
git clone <repository-url>
cd model-manager
pip install -r requirements.txt
```

### Verify Installation

```bash
python3 -m pytest tests/ -v
```

## Usage

### Start Application

```bash
python3 run.py
```

### Keyboard Shortcuts

**Main Screen (Dashboard)**
- `S` - Search for models
- `R` - Refresh model list and check updates
- `Enter` - View model details
- `D` - Delete selected model
- `U` - Update selected model
- `Q` - Quit application

**Search Screen**
- Type to search (500ms debounce)
- `Down` - Jump from search to results
- `Up` - Return to search from first result
- `Enter` - View model details
- `Esc` / `Q` - Go back

**Detail Screen**
- Arrow keys - Navigate quantization table
- `D` - Download selected quantization
- `Enter` - Download selected quantization (works from table)
- `Esc` / `Q` - Go back

**Download Screen**
- `C` / `Esc` - Cancel download

### Download Flow

1. Press `S` to search for models
2. Type keywords (e.g., "llama", "mistral", "phi")
3. Navigate results with arrow keys, press `Enter` on a model
4. View quantizations (table auto-focuses automatically)
5. Navigate to desired quantization, press `Enter` (or `D`)
6. Confirm download in modal
7. Monitor real-time progress with speed, ETA, and file count
8. Download automatically resumes if interrupted

## Project Structure

```
model-manager/
├── run.py                      # Application entry point
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Development dependencies
├── README.md                   # This file
├── CHANGELOG.md                # Version history
├── src/
│   ├── app.py                  # Main Textual application
│   ├── config.py               # Configuration constants
│   ├── theme.py                # Dark theme CSS
│   ├── exceptions.py           # Custom exceptions
│   ├── models.py               # Data models
│   ├── widgets/                # Reusable UI components
│   │   ├── status_badge.py     # Status indicators
│   │   ├── loading.py          # Loading spinner
│   │   ├── section_header.py   # Section headers
│   │   ├── card.py             # Panel containers
│   │   ├── styled_button.py    # Styled buttons
│   │   └── modal.py            # Modal dialogs
│   ├── services/               # Backend services
│   │   ├── hf_client.py        # HuggingFace API wrapper
│   │   ├── storage.py          # Local storage management
│   │   ├── downloader.py       # Download manager with progress tracking
│   │   └── updater.py          # Update checker
│   ├── screens/                # TUI screens
│   │   ├── main_screen.py      # Dashboard with model list
│   │   ├── search_screen.py    # Search interface
│   │   ├── detail_screen.py    # Model details & quantizations
│   │   └── download_screen.py  # Download progress screen
│   └── utils/
│       └── helpers.py          # Utility functions and formatters
├── tests/                      # Unit tests
│   ├── test_downloader.py      # Download manager tests
│   └── test_navigation.py       # Navigation integration tests
└── models/                     # Downloaded models (created on first run)
    ├── .metadata.json          # Model metadata and download history
    └── [author-name]/         # Organized by author/model
        └── model-name/
            ├── *.gguf           # Model files
            └── .cache/         # Temporary download cache
```

## Model Storage

Models are organized by author and model name:

```
models/
├── .metadata.json              # Stores download dates and commit SHAs
└── [author-name]/
    └── [model-name]/
        ├── model-q4_k_m.gguf
        ├── model-q5_k_s.gguf
        └── model-q8_0.gguf
```

### Update Checking

The application automatically checks for model updates:

- **Startup** - Checks all local models for updates
- **Manual** - Press `R` to trigger update check
- **Status Badges** - Visual indicators on main screen

Update statuses:
- **Up to Date** - Model is at latest version
- **Update Available** - Newer version exists
- **Checking** - Update check in progress
- **Error** - Check failed
- **Unknown** - No information available

## Terminal Size

The application adapts to your terminal size:

- **Desktop (80+ cols)** - Full layout with all columns
- **Tablet (60-79 cols)** - Compact layout, some columns hidden
- **Mobile (<60 cols)** - Minimal layout, essential columns only
- **Tiny (<40 cols)** - Cramped layout, may have visual issues

**Recommended:** Minimum 60x24 for good experience, optimal 100x30 or larger

## Troubleshooting

### Download Issues

**Problem:** Download appears stuck or shows incorrect progress

**Solutions:**
1. Check `model_manager.log` for errors
2. Verify internet connection
3. Ensure sufficient disk space
4. Check HuggingFace API status

### Import Errors

**Problem:** `ModuleNotFoundError` when running

**Solution:**
```bash
pip install -r requirements.txt
```

### Terminal Display Issues

**Problem:** Layout looks broken or text overlaps

**Solution:** Ensure terminal is at least 60x24 characters

### Python Version

**Requirement:** Python 3.10 or higher

**Check version:**
```bash
python3 --version
```

## Development

### Code Style

```bash
# Format code
black src/ --line-length 100

# Run tests
python3 -m pytest tests/ -v

# Run specific test
python3 -m pytest tests/test_downloader.py -v
```

### Testing

Test coverage includes:
- Download manager functionality
- Progress calculations
- Resumed download behavior
- Speed calculation accuracy
- Validation logic
- Cancellation handling
- Error scenarios

All tests use pytest with async support (pytest-asyncio).

## Logs

Application logs: `model_manager.log` in project directory

Log levels:
- **DEBUG** - Detailed implementation information
- **INFO** - Normal operations, user actions
- **WARNING** - Non-critical issues, retry attempts
- **ERROR** - Failures and exceptions

## Version History

### v2.5.0 (Current)
- Fixed critical resumed download progress bug
- Improved speed calculation accuracy
- Added color-coded speed visualization
- Enhanced progress display with percentage
- Improved monitoring source selection

See [CHANGELOG.md](CHANGELOG.md) for complete version history.

## License

This project is provided as-is for personal use.

## Acknowledgments

- Built with [Textual](https://textual.textualize.io/) - Modern TUI framework
- Uses [HuggingFace Hub](https://huggingface.co/) - Model repository
- Icons from terminal character sets

---

**Model Manager v2.5.0** - Professional TUI for GGUF model management
