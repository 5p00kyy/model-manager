# Migration Guide: v1.0 to v2.0

## Overview

Model Manager v2.0 is a complete rewrite with a modern TUI interface and improved functionality.

## What's New

### User Interface
- **Textual-based TUI** - Modern, interactive terminal interface
- **Real-time Navigation** - Mouse and keyboard support
- **Multiple Screens** - Dashboard, Search, Detail, and Download views
- **Visual Feedback** - Progress bars, status indicators, notifications

### Download System
- **Accurate Progress** - Per-file progress tracking with speed and ETA
- **Resume Support** - Automatically resumes interrupted downloads
- **Better Tracking** - Individual file progress in multi-file downloads

### Model Management
- **Update Checking** - Async checking for model updates on startup
- **Model Deletion** - Delete unwanted models with confirmation
- **Storage Tracking** - See disk usage at a glance

### Code Architecture
- **Modular Design** - Services separated into logical components
- **Better Logging** - Comprehensive logging throughout
- **Maintainable** - Clean code structure with clear separation of concerns

## Migrating from v1.0

### Models Directory
Your existing `models/` directory is fully compatible. No migration needed.

### Running v2.0
```bash
# Old way
python3 model_manager.py

# New way
python3 run.py
```

### Data Compatibility
- Existing downloads work as-is
- Metadata file `.metadata.json` will be created on first run
- Update checking requires downloading commit SHAs (automatic)

## Keeping v1.0

If you want to keep using v1.0, it's still available as `model_manager.py`.

Both versions can coexist and share the same `models/` directory.

## Differences

| Feature | v1.0 | v2.0 |
|---------|------|------|
| Interface | inquirer prompts | Textual TUI |
| Navigation | Sequential | Multi-screen |
| Progress | Basic | Detailed with ETA |
| Resume | No | Yes |
| Update Check | No | Yes (async) |
| Deletion | Manual | Built-in |
| Storage View | No | Yes |

## Recommendation

Use v2.0 for the best experience. V1.0 remains available as a fallback.
