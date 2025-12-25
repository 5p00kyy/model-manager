# Quick Start Guide

## Installation

```bash
cd /root/model-manager
pip install -r requirements.txt
```

## Run

```bash
python3 run.py
```

## Basic Workflow

### 1. Search for a Model
- Press `S` to open search
- Type "llama" or "mistral" or any model name
- Wait for results (500ms debounce)
- Use arrow keys to navigate results
- Press `Enter` to view details

### 2. Download a Model
- From detail screen, view available quantizations
- Use arrow keys to select a quantization
- Press `D` to start download
- Watch real-time progress with speed and ETA
- Download automatically resumes if interrupted

### 3. Manage Downloaded Models
- Main screen shows all downloaded models
- Press `Enter` to view details
- Press `U` to update if new version available
- Press `D` to delete (with confirmation)
- Press `R` to refresh and check for updates

## Keyboard Shortcuts

### Main Dashboard
| Key | Action |
|-----|--------|
| S | Search for models |
| R | Refresh model list |
| Enter | View model details |
| D | Delete selected model |
| U | Update selected model |
| Q | Quit application |

### Search Screen
| Key | Action |
|-----|--------|
| Type | Search models |
| Enter | View details |
| Esc/Q | Go back |

### Detail Screen
| Key | Action |
|-----|--------|
| D | Download |
| Esc/Q | Go back |

### Download Screen
| Key | Action |
|-----|--------|
| C/Esc | Cancel download |

## Features at a Glance

- **Real-time Search**: Live search with 500ms debounce
- **Accurate Progress**: Per-file progress bars with speed/ETA
- **Resume Downloads**: Automatically resumes interrupted downloads
- **Update Checking**: Async checking on startup (non-blocking)
- **Storage Tracking**: See disk usage at bottom of main screen
- **Model Deletion**: Safe deletion with confirmation dialog

## Tips

1. **First Run**: The app will create a `models/` directory automatically
2. **Update Checking**: Happens in background on startup, doesn't block usage
3. **Large Files**: Multi-part files are grouped and downloaded together
4. **Logs**: Check `model_manager.log` if you encounter issues
5. **Storage**: Main screen shows storage usage at the bottom

## Troubleshooting

### App won't start
```bash
# Check Python version (need 3.7+)
python3 --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Import errors
```bash
# Make sure you're in the right directory
cd /root/model-manager
python3 run.py
```

### Download fails
- Check `model_manager.log` for details
- Verify internet connection
- Ensure sufficient disk space

## Example Session

```
1. Start app:           python3 run.py
2. Press S:             Opens search screen
3. Type "llama-2":      Shows search results
4. Arrow down:          Navigate to desired model
5. Press Enter:         View model details
6. Arrow down:          Select quantization (e.g., Q4_K_M)
7. Press D:             Start download
8. Wait:                Watch progress bars
9. Press Esc:           Return to main screen
10. See downloaded:     Model appears in list
```

## File Locations

- **Downloaded Models**: `/root/model-manager/models/author/model-name/`
- **Logs**: `/root/model-manager/model_manager.log`
- **Metadata**: `/root/model-manager/models/.metadata.json`

## Support

For issues, check:
1. Log file: `model_manager.log`
2. README.md for detailed documentation
3. MIGRATION.md if upgrading from v1.0

Enjoy using Model Manager v2.0!
