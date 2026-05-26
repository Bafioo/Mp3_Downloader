# Setup Commands

This file contains the commands needed to prepare MP3 Downloader on Windows,
macOS, and Linux.

Run the commands from the project folder after cloning the repository.

## Windows

Open PowerShell.

Install Python, Git, and ffmpeg:

```powershell
winget install --id Python.Python.3.13 -e
winget install --id Git.Git -e
winget install --id Gyan.FFmpeg -e
```

Close and reopen PowerShell so PATH changes are loaded.

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, run this once and then activate again:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Install Python dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify the installation:

```powershell
python -c "import tkinter; print('tkinter ok')"
ffmpeg -version
python -m py_compile .\mp3_download.py .\mp3_downloader_gui.py
```

Run the GUI:

```powershell
python .\mp3_downloader_gui.py
```

Run the CLI:

```powershell
python .\mp3_download.py --dry-run
python .\mp3_download.py
```

## macOS

Open Terminal.

Install Homebrew if it is not installed:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install Python, Git, and ffmpeg:

```bash
brew install python git ffmpeg
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify the installation:

```bash
python -c "import tkinter; print('tkinter ok')"
ffmpeg -version
python -m py_compile mp3_download.py mp3_downloader_gui.py
```

If Tkinter is missing when using Homebrew Python, install the matching Tkinter
package or install Python from python.org:

```bash
brew install python-tk@3.13
```

Run the GUI:

```bash
python mp3_downloader_gui.py
```

Run the CLI:

```bash
python mp3_download.py --dry-run
python mp3_download.py
```

## Linux

### Debian / Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-tk ffmpeg git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import tkinter; print('tkinter ok')"
ffmpeg -version
python -m py_compile mp3_download.py mp3_downloader_gui.py
```

### Fedora

```bash
sudo dnf install -y python3 python3-pip python3-tkinter ffmpeg git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import tkinter; print('tkinter ok')"
ffmpeg -version
python -m py_compile mp3_download.py mp3_downloader_gui.py
```

If Fedora cannot find `ffmpeg`, enable RPM Fusion for your Fedora version and
then install `ffmpeg` again.

### Arch Linux

```bash
sudo pacman -Syu --needed python python-pip tk ffmpeg git
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import tkinter; print('tkinter ok')"
ffmpeg -version
python -m py_compile mp3_download.py mp3_downloader_gui.py
```

Run the GUI:

```bash
python mp3_downloader_gui.py
```

Run the CLI:

```bash
python mp3_download.py --dry-run
python mp3_download.py
```

## Optional Security Checks

Install audit tools:

```bash
python -m pip install --upgrade pip-audit bandit
```

Check dependency vulnerabilities:

```bash
python -m pip_audit -r requirements.txt
```

Run a static security scan on the Python code:

```bash
python -m bandit -r . -x .git,.venv,venv,env,__pycache__,downloads
```

