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

On Windows, you can install ffmpeg with:

```powershell
winget install --id Gyan.FFmpeg -e
```

After installing ffmpeg, restart your terminal so the updated PATH is loaded.

## Installation

Clone the repository and install the Python dependency:

```powershell
git clone https://github.com/Bafioo/Mp3_Downloader.git
cd Mp3_Downloader
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

```powershell
copy .\songs.txt.example .\songs.txt
```

## Usage

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

### Command Line

Preview the YouTube search queries without downloading anything:

```powershell
python .\mp3_download.py --dry-run
```

Download the MP3 files into the default `downloads` folder:

```powershell
python .\mp3_download.py
```

Use a custom input file or output folder:

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

## Code Walkthrough

For a detailed explanation of the script's structure and behavior, refer to
[`CODE_WALKTHROUGH.md`](CODE_WALKTHROUGH.md). It provides a practical,
line-by-line overview intended to make the implementation easier to understand
and maintain.

For future maintainers or AI-assisted continuation work, see
[`LLM_HANDOFF.md`](LLM_HANDOFF.md).

## Project Structure

```text
.
|-- mp3_download.py      # Main downloader script
|-- mp3_downloader_gui.py  # Desktop GUI
|-- Images/
|   `-- icon.png         # GUI icon
|-- CODE_WALKTHROUGH.md  # Detailed script explanation
|-- SETUP_COMMANDS.md    # Cross-platform setup commands
|-- LLM_HANDOFF.md       # Continuation briefing for another LLM/developer
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
