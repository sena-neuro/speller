# LSL Recorder Configuration Guide

## Overview

The LSL Recorder has been updated to support cross-platform compatibility and automatic detection of the LabRecorder application. This eliminates the need for hardcoded paths and makes the code work seamlessly on macOS, Windows, and Linux.

## Features

- **Auto-Detection**: Automatically finds the LabRecorder installation on your system
- **Environment Variable Support**: Configure custom paths using `LSL_RECORDER_APP` environment variable
- **Cross-Platform**: Works on macOS, Windows, and Linux
- **Backwards Compatible**: Still accepts `app_root` parameter for explicit path specification

## Configuration Methods (Priority Order)

1. **Explicit Parameter**: Pass `app_root` directly to `LSLRecorder()`
2. **Environment Variable**: Set `LSL_RECORDER_APP` environment variable
3. **Auto-Detection**: Automatic search in common installation locations

## Setup Instructions by Platform

### macOS

#### Option 1: Using Homebrew (Recommended)
```bash
brew install labrecorder
# Auto-detection will find it automatically
```

#### Option 2: Manual Path Configuration
```bash
# Add to ~/.zshrc or ~/.bash_profile
export LSL_RECORDER_APP="/opt/homebrew/Cellar/labrecorder/1.16.5_9/LabRecorder/LabRecorder.app"
```

#### Option 3: Applications Folder
If installed in Applications folder, auto-detection will find it at:
- `~/Applications/LabRecorder.app`
- `/Applications/LabRecorder.app`

### Windows

#### Option 1: Default Installation Path
Auto-detection checks:
- `C:\Program Files\LabRecorder\LabRecorder.exe`
- `C:\Program Files (x86)\LabRecorder\LabRecorder.exe`
- `%LOCALAPPDATA%\LabRecorder\LabRecorder.exe`

#### Option 2: Manual Path Configuration
```powershell
# Set environment variable (Command Prompt)
set LSL_RECORDER_APP=C:\Program Files\LabRecorder\LabRecorder.exe

# Or in PowerShell
[Environment]::SetEnvironmentVariable("LSL_RECORDER_APP", "C:\Program Files\LabRecorder\LabRecorder.exe", "User")
```

### Linux

#### Option 1: System Installation
Auto-detection checks:
- `/usr/local/bin/LabRecorder`
- `/usr/bin/LabRecorder`
- `~/.local/share/applications/LabRecorder`

#### Option 2: Manual Path Configuration
```bash
export LSL_RECORDER_APP="/usr/local/bin/LabRecorder"
```

## Usage Examples

### Basic Usage (Auto-Detection)
```python
from lsl_recorder import LSLRecorder

# Will automatically detect and launch LabRecorder
recorder = LSLRecorder()
recorder.set_recorder(root="~/data", subject="01", session="01", run=1, task="cvep")
recorder.start()
# ... recording ...
recorder.stop()
```

### Explicit Path
```python
from lsl_recorder import LSLRecorder

recorder = LSLRecorder(app_root="/custom/path/to/LabRecorder.app")
```

### Custom Address/Port
```python
from lsl_recorder import LSLRecorder

recorder = LSLRecorder(
    address="localhost",
    port=22345,
    auto_launch=False  # Don't launch the app
)
```

### Finding Installation Path
```python
from lsl_recorder import find_lsl_recorder_app

app_path = find_lsl_recorder_app()
if app_path:
    print(f"Found LabRecorder at: {app_path}")
else:
    print("LabRecorder not found - please install it or set LSL_RECORDER_APP")
```

## Troubleshooting

### "LabRecorder not found"
1. **Verify Installation**: Check if LabRecorder is installed on your system
2. **Check Installation Path**: Use `find_lsl_recorder_app()` to see detected paths
3. **Set Environment Variable**: Explicitly set `LSL_RECORDER_APP` if in non-standard location

### macOS
```bash
# Find LabRecorder installation
find ~/Applications -name "LabRecorder.app" 2>/dev/null
find /Applications -name "LabRecorder.app" 2>/dev/null
find /opt/homebrew -name "LabRecorder.app" 2>/dev/null
find /usr/local -name "LabRecorder.app" 2>/dev/null

# Set the path
export LSL_RECORDER_APP="<found_path>"
```

### Windows
```powershell
# Find LabRecorder installation
Get-ChildItem -Path "C:\Program Files*" -Filter "LabRecorder.exe" -Recurse
Get-ChildItem -Path "$env:LOCALAPPDATA" -Filter "LabRecorder.exe" -Recurse

# Set the path
[Environment]::SetEnvironmentVariable("LSL_RECORDER_APP", "<found_path>", "User")
```

### Linux
```bash
# Find LabRecorder installation
which LabRecorder
find ~ -name "LabRecorder" -type f 2>/dev/null
find /usr -name "LabRecorder" -type f 2>/dev/null

# Set the path
export LSL_RECORDER_APP="<found_path>"
```

## Code Changes Summary

### `lsl_recorder.py`
- Added `find_lsl_recorder_app()` function for platform-aware auto-detection
- Updated `LSLRecorder.__init__()` to support configuration priority
- Replaced platform-specific `os.system("open ...")` with cross-platform subprocess
- Added detailed docstrings and type hints
- Added `_launch_app()` method for platform-specific app launching

### `experiment.py`
- Replaced hardcoded `LSL_RECORDER_APP_DIR` with environment variable lookup
- Added fallback to auto-detection

### New Files
- `.env.example` - Configuration template with platform-specific examples
- `LSL_RECORDER_CONFIG.md` - This guide (create as needed)

## Migration from Old Code

**Old Code:**
```python
LSL_RECORDER_APP_DIR = "/usr/local/opt/labrecorder/LabRecorder/LabRecorder.app"
recorder = LSLRecorder(app_root=LSL_RECORDER_APP_DIR)
```

**New Code (Recommended):**
```python
# No hardcoded path needed - auto-detection handles it
recorder = LSLRecorder()
```

Or with custom path:
```python
import os
app_root = os.environ.get("LSL_RECORDER_APP") or "/your/custom/path"
recorder = LSLRecorder(app_root=app_root)
```
