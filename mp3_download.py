#!/usr/bin/env python3
"""
Scarica in MP3 audio da YouTube partendo da una lista di brani.

Uso previsto: solo contenuti che possiedi, che sono di pubblico dominio,
Creative Commons, o per cui hai esplicita autorizzazione al download.

Formato file input:
  Una canzone per riga, ad esempio:
    Artista   Titolo     
    Artista - Titolo
    Artista;  Titolo
    Artista | Titolo

Righe vuote e righe che iniziano con # vengono ignorate.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


DEFAULT_INPUT_FILE = "songs.txt"
DEFAULT_OUTPUT_DIR = "downloads"


def load_queries(input_file: Path) -> list[str]:
    if not input_file.exists():
        raise FileNotFoundError(f"File non trovato: {input_file}")

    queries: list[str] = []

    with input_file.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            normalized = normalize_song_line(line)
            if not normalized:
                print(f"[WARN] Riga {line_number} ignorata: {line}")
                continue

            queries.append(normalized)

    return queries


def normalize_song_line(line: str) -> str:
    """Converte separatori comuni in una query pulita per YouTube."""
    for separator in (";", "|", ","):
        if separator in line:
            parts = [part.strip() for part in line.split(separator) if part.strip()]
            return " - ".join(parts)

    return line


def find_ffmpeg() -> Path | None:
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
            "Manca yt-dlp. Installa la dipendenza con:\n"
            "  python -m pip install -U yt-dlp"
        ) from exc

    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path is None:
        raise RuntimeError(
            "Manca ffmpeg, necessario per convertire in MP3.\n"
            "Installa ffmpeg e assicurati che il comando 'ffmpeg' sia nel PATH."
        )

    return ffmpeg_path


def download_mp3(
    query: str,
    output_dir: Path,
    archive_file: Path | None,
    ffmpeg_path: Path,
) -> None:
    import yt_dlp

    output_template = str(output_dir / "%(artist,uploader|Unknown)s - %(title)s.%(ext)s")

    options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "default_search": "ytsearch1",
        "outtmpl": output_template,
        "quiet": False,
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

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([query])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cerca brani da un file di testo e li scarica da YouTube in MP3."
    )
    parser.add_argument(
        "-i",
        "--input",
        default=DEFAULT_INPUT_FILE,
        help=f"File con la lista di canzoni/autori. Default: {DEFAULT_INPUT_FILE}",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Cartella dove salvare gli MP3. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Non usare il file archivio per evitare download duplicati.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra le query che verrebbero cercate, senza scaricare nulla.",
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
        print(f"[ERRORE] {exc}", file=sys.stderr)
        return 1

    if not queries:
        print("[INFO] Nessun brano trovato nel file di input.")
        return 0

    print(f"[INFO] Brani trovati: {len(queries)}")

    if args.dry_run:
        for query in queries:
            print(f"  ytsearch1:{query}")
        return 0

    try:
        ffmpeg_path = check_dependencies()
    except RuntimeError as exc:
        print(f"[ERRORE] {exc}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] FFmpeg: {ffmpeg_path}")

    for index, query in enumerate(queries, start=1):
        print(f"\n[{index}/{len(queries)}] Cerco e scarico: {query}")
        try:
            download_mp3(query, output_dir, archive_file, ffmpeg_path)
        except Exception as exc:  # yt-dlp solleva eccezioni diverse in base all'errore.
            print(f"[ERRORE] Download fallito per '{query}': {exc}", file=sys.stderr)

    print(f"\n[FATTO] File salvati in: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
