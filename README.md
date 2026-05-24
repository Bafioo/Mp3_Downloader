# MP3 Downloader

MP3 Downloader is a small Python command-line tool that reads a list of songs,
searches YouTube for each entry, and saves the best audio result as an MP3 file.

It is built on top of [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) and `ffmpeg`,
with a simple text-file workflow that makes it easy to process many tracks at
once.

## Features

- Read songs from a plain-text file
- Search YouTube automatically using the artist and title
- Convert downloaded audio to MP3
- Skip duplicate downloads with a local archive file
- Preview search queries with `--dry-run`
- Keep personal song lists and downloaded audio out of Git

## Requirements

- Python 3.10 or newer
- [`ffmpeg`](https://ffmpeg.org/) installed and available in your system PATH
- Python dependencies from `requirements.txt`

On Windows, you can install ffmpeg with:

```powershell
winget install --id Gyan.FFmpeg -e
```

After installing ffmpeg, restart your terminal so the updated PATH is loaded.

## Installation

Clone the repository and install the Python dependency:

```powershell
git clone https://github.com/YOUR_USERNAME/Mp3_Downloader.git
cd Mp3_Downloader
python -m pip install -U -r requirements.txt
```

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

## Project Structure

```text
.
├── mp3_download.py      # Main downloader script
├── requirements.txt     # Python dependency list
├── songs.txt.example    # Example input file
├── README.md
└── .gitignore
```

## Legal Notice

This tool is intended for downloading content you own, content in the public
domain, Creative Commons content, or content you have explicit permission to
download. Make sure your usage complies with YouTube's Terms of Service and the
copyright laws that apply to you.
