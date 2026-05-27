# MP3 Downloader

MP3 Downloader is a small Python tool that reads a list of songs, searches
YouTube for each entry, and saves the best audio result as an MP3 file. It can
be used from the command line or through a simple desktop interface.

It is built on top of [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) and `ffmpeg`,
with a simple text-file workflow that makes it easy to process many tracks at
once.

## Features

- Read songs from a plain-text file
- Use a simple GUI to choose the song list and output folder
- Download direct YouTube links without creating a song-list file
- Display a custom app icon in the desktop interface
- Search YouTube automatically using the artist and title
- Convert downloaded audio to MP3
- Skip duplicate downloads with a local archive file
- Preview search queries with `--dry-run`
- Keep personal song lists and downloaded audio out of Git

## Requirements

- Python 3.10 or newer
- [`ffmpeg`](https://ffmpeg.org/) installed and available in your system PATH
- Python dependencies from `requirements.txt`
- Tkinter for the desktop GUI

Tkinter is included with the standard Python installer on Windows and macOS. On
some Linux distributions, it may need to be installed separately, for example
with `sudo apt install python3-tk`.

On macOS, install ffmpeg with Homebrew:

```shell
brew install ffmpeg
```

On Windows, you can install ffmpeg with:

```powershell
winget install --id Gyan.FFmpeg -e
```

After installing ffmpeg, open a new terminal if the `ffmpeg` command is not
found immediately.

## Installation

Clone the repository:

```shell
git clone https://github.com/Bafioo/Mp3_Downloader.git
cd Mp3_Downloader
```

Check that your Python version satisfies the requirement:

```shell
python3 --version
```

On macOS, `/usr/bin/python3` may report Python 3.9, which is too old for the
current `yt-dlp` dependency. If so, install Python with Homebrew and create the
virtual environment with the Homebrew interpreter:

```shell
brew install python
"$(brew --prefix)/bin/python3" -m venv .venv
source .venv/bin/activate
```

On Windows, create and activate a virtual environment with Python 3.10 or
newer:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the Python dependency inside the activated virtual environment:

```shell
python -m pip install -U pip
python -m pip install -U -r requirements.txt
```

For complete Windows, macOS, and Linux setup commands, see
[`SETUP_COMMANDS.md`](SETUP_COMMANDS.md).

## Song List

Create a `songs.txt` file in the project folder. Add one song per line:

```text
Artist - Title
Artist; Title
Artist | Title
```

Blank lines and lines starting with `#` are ignored.

You can start from the included template:

On macOS:

```shell
cp songs.txt.example songs.txt
```

On Windows:

```powershell
copy .\songs.txt.example .\songs.txt
```

## Usage

The project has two entry points:

- `mp3_download.py` contains the core download logic and the command-line
  interface.
- `mp3_downloader_gui.py` is the desktop interface. It imports and uses the
  functions from `mp3_download.py`, so both files must stay in the same project
  folder.

### Desktop GUI

Launch the graphical interface:

```powershell
python .\mp3_downloader_gui.py
```

From the GUI you can:

- Choose the output folder for downloaded MP3 files
- Select a text file containing song names from the **Song list** tab
- Paste one or more direct YouTube URLs from the **YouTube links** tab, using one link per line
- Enable or disable duplicate-download tracking
- Read an activity log with the current download title, estimated time remaining, and completion status
- Start the download without typing command-line arguments

### GUI Tutorial

1. Activate the virtual environment you created during installation.

   On macOS:

   ```shell
   source .venv/bin/activate
   ```

   On Windows:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. Start the GUI:

   On macOS:

   ```shell
   python mp3_downloader_gui.py
   ```

   On Windows:

   ```powershell
   python .\mp3_downloader_gui.py
   ```

3. Choose the output folder.

   This is where the downloaded MP3 files will be saved. The default folder is
   `downloads`.

4. Choose how to provide songs.

   In the **Song list** tab, click **Browse** and select a text file containing
   one song per line, for example:

   ```text
   Artist - Title
   Artist; Title
   Artist | Title
   ```

   In the **YouTube links** tab, paste one or more direct YouTube URLs, using
   one link per line.

5. Keep duplicate protection enabled unless you want to download the same video
   again.

   When enabled, the app writes a `downloaded.txt` archive inside the output
   folder and uses it to skip videos that were already downloaded.

6. Start the download.

   The activity log shows the current title, estimated time remaining, matched
   result, completion status, or failure reason.

### Command Line

Preview the YouTube search queries without downloading anything:

On macOS:

```shell
source .venv/bin/activate
python mp3_download.py --dry-run
```

On Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python .\mp3_download.py --dry-run
```

Download the MP3 files into the default `downloads` folder:

On macOS:

```shell
python mp3_download.py
```

On Windows:

```powershell
python .\mp3_download.py
```

Use a custom input file or output folder:

On macOS:

```shell
python mp3_download.py -i my_songs.txt -o music
```

On Windows:

```powershell
python .\mp3_download.py -i .\my_songs.txt -o .\music
```

## CLI Options

```text
-i, --input       Input text file with the song list
-o, --output      Folder where MP3 files will be saved
--dry-run         Show search queries without downloading
--no-archive      Disable the duplicate-download archive
```

By default, the script creates `downloads/downloaded.txt` to avoid downloading
the same YouTube video more than once.

## Project Structure

```text
.
|-- mp3_download.py      # Main downloader script
|-- mp3_downloader_gui.py  # Desktop GUI
|-- Images/
|   `-- icon.png         # GUI icon
|-- SETUP_COMMANDS.md    # Cross-platform setup commands
|-- requirements.txt     # Python dependency list
|-- songs.txt.example    # Example input file
|-- README.md
`-- .gitignore
```

## Legal Notice

This tool is intended for downloading content you own, content in the public
domain, Creative Commons content, or content you have explicit permission to
download. Make sure your usage complies with YouTube's Terms of Service and the
copyright laws that apply to you.
