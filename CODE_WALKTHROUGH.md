# Code Walkthrough

This document explains what `mp3_download.py` does, almost line by line.
It is written as a practical guide: each section follows the code order and
explains why that part exists.

## Header And Script Description

```python
#!/usr/bin/env python3
```

Tells Unix-like systems to run this file with Python 3 when the script is
executed directly. On Windows it is mostly harmless, but still useful for
cross-platform compatibility.

```python
"""
Download MP3 audio from YouTube using a plain-text list of songs.
...
"""
```

This is the module docstring. It describes the purpose of the script, the
intended legal use, the accepted input format, and the fact that blank/comment
lines are ignored.

## Imports

```python
from __future__ import annotations
```

Postpones evaluation of type annotations. This keeps type hints lightweight and
helps compatibility when using modern type syntax.

```python
import argparse
```

Loads Python's standard command-line argument parser. The script uses it for
options like `--input`, `--output`, and `--dry-run`.

```python
import os
```

Gives access to operating-system environment variables. Here it is used to read
`LOCALAPPDATA` on Windows when searching for an ffmpeg installation.

```python
import shutil
```

Provides utility functions. The script uses `shutil.which("ffmpeg")` to check
whether ffmpeg is available from the terminal PATH.

```python
import sys
```

Gives access to system-level objects. The script uses `sys.stderr` to print
error messages separately from normal output.

```python
from pathlib import Path
```

Imports `Path`, a clean object-oriented way to work with file and folder paths.

## Defaults

```python
DEFAULT_INPUT_FILE = "songs.txt"
```

Defines the default input file. If the user does not pass `--input`, the script
looks for `songs.txt`.

```python
DEFAULT_OUTPUT_DIR = "downloads"
```

Defines the default output folder. If the user does not pass `--output`, MP3
files are saved inside `downloads`.

## Loading The Song List

```python
def load_queries(input_file: Path) -> list[str]:
```

Defines a function that receives a file path and returns a list of YouTube
search queries as strings.

```python
    if not input_file.exists():
```

Checks whether the selected input file actually exists.

```python
        raise FileNotFoundError(f"File not found: {input_file}")
```

Stops this function with a clear error if the file is missing.

```python
    queries: list[str] = []
```

Creates an empty list. Valid song lines will be added here.

```python
    with input_file.open("r", encoding="utf-8") as file:
```

Opens the input file in read mode using UTF-8, so song names with international
characters can be read correctly. The `with` block closes the file
automatically.

```python
        for line_number, raw_line in enumerate(file, start=1):
```

Loops through the file one line at a time. `line_number` starts from 1 so warning
messages match normal editor line numbers.

```python
            line = raw_line.strip()
```

Removes spaces and line breaks from the start and end of the current line.

```python
            if not line or line.startswith("#"):
```

Checks whether the line is empty or starts with `#`.

```python
                continue
```

Skips empty lines and comment lines.

```python
            normalized = normalize_song_line(line)
```

Converts the current song line into a cleaner YouTube search query.

```python
            if not normalized:
```

Checks whether normalization produced an empty result.

```python
                print(f"[WARN] Skipped line {line_number}: {line}")
```

Prints a warning showing which line was skipped.

```python
                continue
```

Moves to the next line instead of adding a bad query.

```python
            queries.append(normalized)
```

Adds the cleaned search query to the list.

```python
    return queries
```

Returns the final list of queries to the caller.

## Normalizing Song Lines

```python
def normalize_song_line(line: str) -> str:
```

Defines a function that receives one line from the input file and returns a
cleaner search string.

```python
    """Convert common separators into a clean YouTube search query."""
```

Short function docstring. It explains the function's purpose.

```python
    for separator in (";", "|", ","):
```

Checks a few common separators users might use between artist and title.

```python
        if separator in line:
```

Runs the next block only if the current separator exists in the line.

```python
            parts = [part.strip() for part in line.split(separator) if part.strip()]
```

Splits the line using that separator, trims each piece, and removes empty
pieces.

```python
            return " - ".join(parts)
```

Joins the cleaned pieces with ` - `, which creates a natural YouTube search
query like `Artist - Title`.

```python
    return line
```

If no special separator is found, returns the line unchanged.

## Finding ffmpeg

```python
def find_ffmpeg() -> Path | None:
```

Defines a function that tries to locate `ffmpeg`. It returns a `Path` if found,
or `None` if not found.

```python
    ffmpeg_path = shutil.which("ffmpeg")
```

Checks if the command `ffmpeg` is available in the current PATH.

```python
    if ffmpeg_path:
```

Checks whether `shutil.which` found something.

```python
        return Path(ffmpeg_path)
```

Returns the ffmpeg executable path as a `Path` object.

```python
    local_app_data = os.environ.get("LOCALAPPDATA")
```

Reads the Windows `LOCALAPPDATA` environment variable. This is where winget
often stores user-installed packages.

```python
    if not local_app_data:
```

Checks whether that environment variable is missing.

```python
        return None
```

Stops searching because the winget fallback path cannot be built.

```python
    winget_packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
```

Builds the folder path where winget packages are commonly installed.

```python
    if not winget_packages.exists():
```

Checks whether that folder exists.

```python
        return None
```

Stops searching if the winget packages folder is not present.

```python
    matches = sorted(winget_packages.glob("Gyan.FFmpeg_*/*/bin/ffmpeg.exe"))
```

Looks for ffmpeg installed by the `Gyan.FFmpeg` winget package. Sorting makes
the result deterministic.

```python
    if matches:
```

Checks whether at least one matching ffmpeg executable was found.

```python
        return matches[-1]
```

Returns the last sorted match. In practice this usually points to the newest
matching installation.

```python
    return None
```

Returns `None` when ffmpeg cannot be found anywhere.

## Checking Dependencies

```python
def check_dependencies() -> Path:
```

Defines a function that verifies the tools needed for downloading and MP3
conversion.

```python
    try:
```

Starts a block where an import might fail.

```python
        import yt_dlp  # noqa: F401
```

Tries to import `yt-dlp`. The `# noqa: F401` comment tells linters that this
import is intentionally unused, because it is only a dependency check.

```python
    except ImportError as exc:
```

Catches the error raised when `yt-dlp` is not installed.

```python
        raise RuntimeError(
            "yt-dlp is missing. Install the dependency with:\n"
            "  python -m pip install -U yt-dlp"
        ) from exc
```

Raises a clearer user-facing error that explains how to install `yt-dlp`.

```python
    ffmpeg_path = find_ffmpeg()
```

Searches for ffmpeg using the helper function described above.

```python
    if ffmpeg_path is None:
```

Checks whether ffmpeg was not found.

```python
        raise RuntimeError(
            "ffmpeg is missing, and it is required to convert audio to MP3.\n"
            "Install ffmpeg and make sure the 'ffmpeg' command is available in PATH."
        )
```

Raises a clear error explaining that MP3 conversion requires ffmpeg.

```python
    return ffmpeg_path
```

Returns the ffmpeg path so the downloader can pass it to `yt-dlp`.

## Downloading One MP3

```python
def download_mp3(
    query: str,
    output_dir: Path,
    archive_file: Path | None,
    ffmpeg_path: Path,
) -> None:
```

Defines the function that downloads one song. It receives the search query, the
output folder, the optional archive file, and the ffmpeg path.

```python
    import yt_dlp
```

Imports `yt-dlp` inside the function. This keeps startup lightweight and lets
`check_dependencies` produce a cleaner error first.

```python
    output_template = str(output_dir / "%(artist,uploader|Unknown)s - %(title)s.%(ext)s")
```

Builds the output filename pattern. `yt-dlp` fills in metadata such as artist,
uploader, title, and extension. If artist/uploader is missing, it uses
`Unknown`.

```python
    options = {
```

Starts the dictionary of options passed to `yt-dlp`.

```python
        "format": "bestaudio/best",
```

Tells `yt-dlp` to download the best available audio stream.

```python
        "noplaylist": True,
```

Prevents accidental playlist downloads. Only one result should be processed.

```python
        "default_search": "ytsearch1",
```

If the input is not a URL, search YouTube and take the first result.

```python
        "outtmpl": output_template,
```

Sets the output filename pattern created earlier.

```python
        "quiet": False,
```

Allows `yt-dlp` to print progress and useful messages.

```python
        "ignoreerrors": True,
```

Lets `yt-dlp` continue gracefully when one item fails.

```python
        "ffmpeg_location": str(ffmpeg_path.parent),
```

Points `yt-dlp` to the folder that contains ffmpeg.

```python
        "postprocessors": [
```

Starts the list of post-processing steps that run after downloading.

```python
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
```

Configures ffmpeg extraction: convert the downloaded audio to MP3 at 192 kbps.

```python
        ],
    }
```

Closes the postprocessor list and the options dictionary.

```python
    if archive_file is not None:
```

Checks whether duplicate-download tracking is enabled.

```python
        options["download_archive"] = str(archive_file)
```

Adds a `yt-dlp` archive file. Videos already listed there will be skipped in
future runs.

```python
    with yt_dlp.YoutubeDL(options) as ydl:
```

Creates a `yt-dlp` downloader instance using the configured options. The `with`
block handles cleanup.

```python
        ydl.download([query])
```

Runs the actual search/download for this single query.

## Parsing Command-Line Options

```python
def parse_args() -> argparse.Namespace:
```

Defines a function that reads command-line arguments and returns them as an
object.

```python
    parser = argparse.ArgumentParser(
        description="Search songs from a text file and download them from YouTube as MP3."
    )
```

Creates the command-line parser and sets the description shown in `--help`.

```python
    parser.add_argument(
        "-i",
        "--input",
        default=DEFAULT_INPUT_FILE,
        help=f"Text file with the song/artist list. Default: {DEFAULT_INPUT_FILE}",
    )
```

Adds `-i` and `--input`. This lets users choose a custom song-list file.

```python
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Folder where MP3 files will be saved. Default: {DEFAULT_OUTPUT_DIR}",
    )
```

Adds `-o` and `--output`. This lets users choose where MP3 files are saved.

```python
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Do not use the archive file that prevents duplicate downloads.",
    )
```

Adds `--no-archive`. When present, the value becomes `True` and duplicate
tracking is disabled.

```python
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the queries that would be searched without downloading anything.",
    )
```

Adds `--dry-run`. When present, the script prints the search queries and exits
without downloading.

```python
    return parser.parse_args()
```

Parses the command-line arguments and returns the result.

## Main Program Flow

```python
def main() -> int:
```

Defines the main function. It returns an exit code: `0` for success, `1` for an
error.

```python
    args = parse_args()
```

Reads all command-line options.

```python
    input_file = Path(args.input).expanduser().resolve()
```

Converts the input argument into an absolute path. `expanduser()` supports paths
like `~/songs.txt`.

```python
    output_dir = Path(args.output).expanduser().resolve()
```

Converts the output folder argument into an absolute path.

```python
    archive_file = None if args.no_archive else output_dir / "downloaded.txt"
```

Decides whether to use a duplicate-download archive. If `--no-archive` is used,
there is no archive file; otherwise it uses `downloaded.txt` in the output
folder.

```python
    try:
        queries = load_queries(input_file)
```

Attempts to read and normalize all songs from the input file.

```python
    except OSError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
```

Handles file-related errors, prints them as errors, and exits with code `1`.

```python
    if not queries:
```

Checks whether the input file contained no usable songs.

```python
        print("[INFO] No songs found in the input file.")
        return 0
```

Prints an informational message and exits successfully, because this is not a
crash.

```python
    print(f"[INFO] Songs found: {len(queries)}")
```

Shows how many songs will be processed.

```python
    if args.dry_run:
```

Checks whether the user requested preview mode.

```python
        for query in queries:
            print(f"  ytsearch1:{query}")
        return 0
```

Prints every YouTube search query and exits without downloading anything.

```python
    try:
        ffmpeg_path = check_dependencies()
```

Checks that `yt-dlp` and ffmpeg are available before downloading.

```python
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
```

Handles missing dependency errors and exits with code `1`.

```python
    output_dir.mkdir(parents=True, exist_ok=True)
```

Creates the output folder if it does not exist. Parent folders are created too.

```python
    print(f"[INFO] FFmpeg: {ffmpeg_path}")
```

Shows which ffmpeg executable will be used.

```python
    for index, query in enumerate(queries, start=1):
```

Loops through every song query. `index` starts from 1 for human-friendly
progress messages.

```python
        print(f"\n[{index}/{len(queries)}] Searching and downloading: {query}")
```

Prints progress before each download.

```python
        try:
            download_mp3(query, output_dir, archive_file, ffmpeg_path)
```

Attempts to download and convert the current query.

```python
        except Exception as exc:  # yt-dlp raises different exceptions depending on the error.
```

Catches any download/conversion error for the current song. The comment explains
why this uses a broad exception handler.

```python
            print(f"[ERROR] Download failed for '{query}': {exc}", file=sys.stderr)
```

Prints the failure but does not stop the whole batch.

```python
    print(f"\n[DONE] Files saved in: {output_dir}")
```

Prints the final output folder after all songs have been processed.

```python
    return 0
```

Returns a success exit code.

## Script Entry Point

```python
if __name__ == "__main__":
```

Checks whether this file is being run directly instead of imported by another
Python file.

```python
    raise SystemExit(main())
```

Runs `main()` and exits the program using the returned exit code.

