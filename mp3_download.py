#!/usr/bin/env python3
"""
Download MP3 audio from YouTube using a plain-text list of songs.

Intended use: only download content you own, content in the public domain,
Creative Commons content, or content you have explicit permission to download.

Input file format:
  One song per line, for example:
    Artist - Title
    Artist; Title
    Artist | Title

Blank lines and lines starting with # are ignored.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Callable


DEFAULT_INPUT_FILE = "songs.txt"
DEFAULT_OUTPUT_DIR = "downloads"


def load_queries(input_file: Path) -> list[str]:
    if not input_file.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    queries: list[str] = []

    with input_file.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            normalized = normalize_song_line(line)
            if not normalized:
                print(f"[WARN] Skipped line {line_number}: {line}")
                continue

            queries.append(normalized)

    return queries


def normalize_song_line(line: str) -> str:
    """Convert common separators into a clean YouTube search query."""
    for separator in (";", "|", ","):
        if separator in line:
            parts = [part.strip() for part in line.split(separator) if part.strip()]
            return " - ".join(parts)

    return line


def find_ffmpeg() -> Path | None:
    executable_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"

    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        bundled_ffmpeg = Path(bundled_root) / executable_name
        if bundled_ffmpeg.exists():
            return bundled_ffmpeg

    executable_dir = Path(sys.executable).resolve().parent
    bundled_ffmpeg = executable_dir / executable_name
    if bundled_ffmpeg.exists():
        return bundled_ffmpeg

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return Path(ffmpeg_path)

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None

    winget_packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    if not winget_packages.exists():
        return None

    matches = sorted(winget_packages.glob("Gyan.FFmpeg_*/*/bin/ffmpeg.exe"))
    if matches:
        return matches[-1]

    return None


def check_dependencies() -> Path:
    try:
        import yt_dlp  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "yt-dlp is missing. Install the dependency with:\n"
            "  python -m pip install -U yt-dlp"
        ) from exc

    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path is None:
        raise RuntimeError(
            "ffmpeg is missing, and it is required to convert audio to MP3.\n"
            "Install ffmpeg and make sure the 'ffmpeg' command is available in PATH."
        )

    return ffmpeg_path


def get_download_title(info: dict | None, fallback: str) -> str:
    if not info:
        return fallback

    entries = info.get("entries")
    if entries:
        first_entry = next((entry for entry in entries if entry), None)
        if first_entry:
            return get_download_title(first_entry, fallback)

    title = info.get("title")
    uploader = info.get("uploader") or info.get("artist")

    if title and uploader:
        return f"{uploader} - {title}"
    if title:
        return str(title)

    return fallback


def download_mp3(
    query: str,
    output_dir: Path,
    archive_file: Path | None,
    ffmpeg_path: Path,
    quiet: bool = False,
    progress_hook: Callable[[dict[str, Any]], None] | None = None,
) -> str:
    import yt_dlp

    output_template = str(output_dir / "%(artist,uploader|Unknown)s - %(title)s.%(ext)s")

    options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "default_search": "ytsearch1",
        "outtmpl": output_template,
        "quiet": quiet,
        "no_warnings": quiet,
        "ignoreerrors": True,
        "ffmpeg_location": str(ffmpeg_path.parent),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    if archive_file is not None:
        options["download_archive"] = str(archive_file)

    if progress_hook is not None:
        options["progress_hooks"] = [progress_hook]

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(query, download=True)

    if info is None:
        raise RuntimeError("No downloadable result was found.")

    return get_download_title(info, query)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search songs from a text file and download them from YouTube as MP3."
    )
    parser.add_argument(
        "-i",
        "--input",
        default=DEFAULT_INPUT_FILE,
        help=f"Text file with the song/artist list. Default: {DEFAULT_INPUT_FILE}",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Folder where MP3 files will be saved. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Do not use the archive file that prevents duplicate downloads.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the queries that would be searched without downloading anything.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_file = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()
    archive_file = None if args.no_archive else output_dir / "downloaded.txt"

    try:
        queries = load_queries(input_file)
    except OSError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if not queries:
        print("[INFO] No songs found in the input file.")
        return 0

    print(f"[INFO] Songs found: {len(queries)}")

    if args.dry_run:
        for query in queries:
            print(f"  ytsearch1:{query}")
        return 0

    try:
        ffmpeg_path = check_dependencies()
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] FFmpeg: {ffmpeg_path}")

    for index, query in enumerate(queries, start=1):
        print(f"\n[{index}/{len(queries)}] Searching and downloading: {query}")
        try:
            download_mp3(query, output_dir, archive_file, ffmpeg_path)
        except Exception as exc:  # yt-dlp raises different exceptions depending on the error.
            print(f"[ERROR] Download failed for '{query}': {exc}", file=sys.stderr)

    print(f"\n[DONE] Files saved in: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
