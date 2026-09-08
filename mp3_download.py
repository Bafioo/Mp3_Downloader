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
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


DEFAULT_INPUT_FILE = "songs.txt"
DEFAULT_OUTPUT_DIR = "downloads"
DEFAULT_COOKIES_FILE = "cookies.txt"
YTDLP_EJS_INSTALL_COMMAND = 'python -m pip install -U "yt-dlp[default]"'
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


@dataclass(frozen=True)
class JavascriptRuntime:
    name: str
    path: Path
    version: str | None = None


@dataclass(frozen=True)
class RuntimeDependencies:
    ffmpeg_path: Path
    ffprobe_path: Path | None
    javascript_runtime: JavascriptRuntime


ERROR_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "JAVASCRIPT RUNTIME ERROR",
        (
            "javascript runtime",
            "js runtime",
            "jsc",
            "ejs",
            "node",
            "deno",
            "quickjs",
            "n challenge",
            "signature",
        ),
    ),
    (
        "FFMPEG ERROR",
        ("ffmpeg", "ffprobe", "postprocess", "post-process", "unable to convert"),
    ),
    (
        "CONNECTION ERROR",
        (
            "urlopen",
            "connection",
            "timeout",
            "network",
            "socket",
            "ssl",
            "failed to connect",
            "failed to resolve",
            "getaddrinfo",
            "dns",
            "temporarily unavailable",
        ),
    ),
    (
        "AUTH ERROR",
        ("403", "forbidden", "sign in", "login", "cookies", "not a bot", "captcha", "dpapi"),
    ),
    (
        "API ERROR",
        ("quota", "rate limit", "too many requests", "429"),
    ),
    (
        "NO RESULT",
        (
            "no downloadable",
            "no video",
            "no result",
            "unable to extract",
            "unsupported url",
        ),
    ),
)


def _ensure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


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


def _platform_executable_name(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def _safe_exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def _safe_iter_dirs(path: Path) -> list[Path]:
    try:
        children = list(path.iterdir())
    except OSError:
        return []

    dirs: list[Path] = []
    for child in children:
        try:
            if child.is_dir():
                dirs.append(child)
        except OSError:
            continue

    return sorted(dirs, key=lambda candidate: candidate.name.lower(), reverse=True)


def _unique_paths(paths: Iterable[Path]) -> Iterable[Path]:
    seen: set[str] = set()

    for path in paths:
        key = str(path).lower() if os.name == "nt" else str(path)
        if key in seen:
            continue

        seen.add(key)
        yield path


def _check_executable_output(
    executable: Path,
    args: tuple[str, ...],
    timeout: int = 8,
) -> str | None:
    try:
        completed = subprocess.run(
            [str(executable), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if completed.returncode != 0:
        return None

    return "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    )


def _is_usable_executable(executable: Path, args: tuple[str, ...]) -> bool:
    return _check_executable_output(executable, args) is not None


def _candidate_from_env(env_var: str, executable_name: str) -> Path | None:
    configured = os.environ.get(env_var)
    if not configured:
        return None

    candidate = Path(configured).expanduser()
    if candidate.suffix or candidate.name.lower() == executable_name.lower():
        return candidate

    return candidate / executable_name


def _iter_bundled_executable_candidates(executable_name: str) -> Iterable[Path]:
    bundled_root = getattr(sys, "_MEIPASS", None)
    roots = [
        Path(bundled_root) if bundled_root else None,
        Path(sys.executable).resolve().parent,
        Path(__file__).resolve().parent,
    ]

    for root in roots:
        if root is None:
            continue

        yield root / executable_name
        yield root / "bin" / executable_name


def find_cookies_file() -> Path | None:
    configured = os.environ.get("MP3_DOWNLOADER_COOKIES_FILE")
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())

    bundled_root = getattr(sys, "_MEIPASS", None)
    roots = [
        Path(sys.executable).resolve().parent,
        Path(bundled_root) if bundled_root else None,
        Path(__file__).resolve().parent,
        Path.cwd(),
    ]
    for root in roots:
        if root is not None:
            candidates.append(root / DEFAULT_COOKIES_FILE)

    for candidate in _unique_paths(candidates):
        if _safe_exists(candidate):
            return candidate

    return None


def _iter_winget_ffmpeg_candidates(executable_name: str) -> Iterable[Path]:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if os.name != "nt" or not local_app_data:
        return

    winget_packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    if not _safe_exists(winget_packages):
        return

    try:
        package_dirs = list(winget_packages.glob("Gyan.FFmpeg_*"))
    except OSError:
        return

    for package_dir in sorted(
        package_dirs,
        key=lambda candidate: candidate.name.lower(),
        reverse=True,
    ):
        for build_dir in _safe_iter_dirs(package_dir):
            yield build_dir / "bin" / executable_name


def _iter_ffmpeg_candidates(executable_name: str) -> Iterable[Path]:
    env_candidate = _candidate_from_env("MP3_DOWNLOADER_FFMPEG_PATH", executable_name)
    if env_candidate is not None:
        yield env_candidate

    yield from _iter_bundled_executable_candidates(executable_name)

    path_candidate = shutil.which(executable_name)
    if path_candidate:
        yield Path(path_candidate)

    yield from _iter_winget_ffmpeg_candidates(executable_name)


def _looks_like_winget_ffmpeg_candidate(path: Path, executable_name: str) -> bool:
    normalized = str(path).lower()
    return (
        os.name == "nt"
        and "\\microsoft\\winget\\packages\\gyan.ffmpeg_" in normalized
        and normalized.endswith(f"\\bin\\{executable_name.lower()}")
    )


def find_ffmpeg() -> Path | None:
    executable_name = _platform_executable_name("ffmpeg")
    winget_fallback: Path | None = None

    for candidate in _unique_paths(_iter_ffmpeg_candidates(executable_name)):
        if _is_usable_executable(candidate, ("-version",)):
            return candidate

        if _looks_like_winget_ffmpeg_candidate(candidate, executable_name):
            winget_fallback = winget_fallback or candidate

    return winget_fallback


def find_ffprobe(ffmpeg_path: Path | None = None) -> Path | None:
    executable_name = _platform_executable_name("ffprobe")
    winget_fallback: Path | None = None

    candidates: list[Path] = []
    if ffmpeg_path is not None:
        candidates.append(ffmpeg_path.parent / executable_name)

    candidates.extend(_iter_ffmpeg_candidates(executable_name))

    for candidate in _unique_paths(candidates):
        if _is_usable_executable(candidate, ("-version",)):
            return candidate

        if _looks_like_winget_ffmpeg_candidate(candidate, executable_name):
            winget_fallback = winget_fallback or candidate

    return winget_fallback


def _runtime_executable_names(runtime_name: str) -> tuple[str, ...]:
    names = {
        "deno": ("deno",),
        "node": ("node",),
        "quickjs": ("qjs", "quickjs"),
        "bun": ("bun",),
    }.get(runtime_name, (runtime_name,))
    return tuple(_platform_executable_name(name) for name in names)


def _parse_version_tuple(output: str) -> tuple[int, ...] | None:
    match = re.search(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", output)
    if not match:
        return None

    return tuple(int(part) for part in match.groups(default="0"))


def _version_meets_requirement(
    runtime_name: str,
    version: tuple[int, ...] | None,
) -> bool:
    if version is None:
        return True

    minimum_versions = {
        "deno": (2, 3, 0),
        "node": (22, 0, 0),
        "quickjs": (2023, 12, 9),
        "bun": (1, 2, 11),
    }
    maximum_versions = {
        "bun": (1, 3, 14),
    }

    minimum_version = minimum_versions.get(runtime_name)
    maximum_version = maximum_versions.get(runtime_name)

    if minimum_version and version < minimum_version:
        return False

    if maximum_version and version > maximum_version:
        return False

    return True


def _iter_javascript_runtime_names() -> Iterable[str]:
    configured_runtime = os.environ.get("MP3_DOWNLOADER_JS_RUNTIME")
    if configured_runtime:
        yield configured_runtime.lower()

    yield from ("deno", "node", "quickjs")


def _iter_javascript_runtime_candidates(runtime_name: str) -> Iterable[Path]:
    env_candidate = os.environ.get(f"MP3_DOWNLOADER_{runtime_name.upper()}_PATH")

    for executable_name in _runtime_executable_names(runtime_name):
        if env_candidate:
            configured_path = Path(env_candidate).expanduser()
            yield (
                configured_path / executable_name
                if not configured_path.suffix
                else configured_path
            )

        yield from _iter_bundled_executable_candidates(executable_name)

        path_candidate = shutil.which(executable_name)
        if path_candidate:
            yield Path(path_candidate)


def find_javascript_runtime() -> JavascriptRuntime | None:
    for runtime_name in dict.fromkeys(_iter_javascript_runtime_names()):
        for candidate in _unique_paths(_iter_javascript_runtime_candidates(runtime_name)):
            output = _check_executable_output(candidate, ("--version",))
            if output is None:
                continue

            version = _parse_version_tuple(output or "")
            if not _version_meets_requirement(runtime_name, version):
                continue

            version_text = ".".join(str(part) for part in version) if version else None
            return JavascriptRuntime(runtime_name, candidate, version_text)

    return None


def check_dependencies() -> RuntimeDependencies:
    try:
        import yt_dlp  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "yt-dlp is missing. Install the dependency with:\n"
            f"  {YTDLP_EJS_INSTALL_COMMAND}"
        ) from exc

    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path is None:
        raise RuntimeError(
            "ffmpeg is missing, and it is required to convert audio to MP3.\n"
            "Install ffmpeg and make sure the 'ffmpeg' command is available in PATH, "
            "or set MP3_DOWNLOADER_FFMPEG_PATH to the ffmpeg executable or bin folder."
        )

    javascript_runtime = find_javascript_runtime()
    if javascript_runtime is None:
        raise RuntimeError(
            "No supported JavaScript runtime was found. Recent yt-dlp versions need "
            "one for full YouTube support.\n"
            "Install Deno 2.3+ or Node.js 22+, then reopen the terminal so PATH is "
            "refreshed. You can also set MP3_DOWNLOADER_JS_RUNTIME=node and "
            "MP3_DOWNLOADER_NODE_PATH to node.exe."
        )

    return RuntimeDependencies(
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=find_ffprobe(ffmpeg_path),
        javascript_runtime=javascript_runtime,
    )


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


def short_error(exc: BaseException, max_length: int = 240) -> str:
    message = ANSI_ESCAPE_RE.sub("", str(exc)).strip() or exc.__class__.__name__
    first_line = next(
        (line.strip() for line in message.splitlines() if line.strip()),
        message,
    )
    return first_line[:max_length]


def classify_download_error(exc: BaseException) -> tuple[str, str]:
    detail = short_error(exc)
    lower_detail = str(exc).lower()

    if "sign in to confirm your age" in lower_detail:
        return (
            "AUTH ERROR",
            "video con limite eta/login. esporta cookies.txt e mettilo accanto all'app.",
        )

    for category, keywords in ERROR_CATEGORIES:
        if any(keyword in lower_detail for keyword in keywords):
            return category, detail

    return "DOWNLOAD ERROR", detail


def build_ydl_options(
    output_dir: Path,
    archive_file: Path | None,
    ffmpeg_path: Path,
    quiet: bool,
    progress_hook: Callable[[dict[str, Any]], None] | None,
    js_runtime: JavascriptRuntime | None,
    cookies_browser: str | None = None,
) -> dict[str, Any]:
    output_template = str(
        output_dir / "%(artist,uploader|Unknown)s - %(title)s.%(ext)s"
    )

    class YtDlpLogger:
        def debug(self, msg: str) -> None:
            pass

        def info(self, msg: str) -> None:
            pass

        def warning(self, msg: str) -> None:
            if not quiet:
                print(f"[YT-DLP WARNING] {msg}", file=sys.stderr)

        def error(self, msg: str) -> None:
            if not quiet:
                print(f"[YT-DLP ERROR] {msg}", file=sys.stderr)

    options: dict[str, Any] = {
        "format": "bestaudio[ext=m4a]/bestaudio",
        "noplaylist": True,
        "default_search": "ytsearch1",
        "outtmpl": output_template,
        "logger": YtDlpLogger(),
        "quiet": quiet,
        "no_warnings": quiet,
        "ignoreerrors": False,
        "ffmpeg_location": str(ffmpeg_path.parent),
        "remote_components": [],
        "source_address": os.environ.get("MP3_DOWNLOADER_SOURCE_ADDRESS", "0.0.0.0"),
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 3,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    if js_runtime is not None:
        options["js_runtimes"] = {js_runtime.name: {"path": str(js_runtime.path)}}

    try:
        import curl_cffi  # noqa: F401
        from yt_dlp.networking.impersonate import ImpersonateTarget

        options["impersonate"] = ImpersonateTarget.from_str("chrome")
    except Exception:
        pass

    cookies_file = find_cookies_file()
    if cookies_file:
        options["cookiefile"] = str(cookies_file)

    cookies_browser = cookies_browser or os.environ.get("MP3_DOWNLOADER_COOKIES_BROWSER")
    if cookies_browser:
        options["cookiesfrombrowser"] = (cookies_browser,)

    if archive_file is not None:
        options["download_archive"] = str(archive_file)

    if progress_hook is not None:
        options["progress_hooks"] = [progress_hook]

    return options


def _is_forbidden_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "403" in text or "forbidden" in text


def _is_cookie_load_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "cookie" in text and (
        "could not copy" in text
        or "could not find" in text
        or "permission denied" in text
        or "failed to load cookies" in text
    )


def _is_age_or_login_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "sign in to confirm your age" in text or "confirm your age" in text


def _looks_like_url(value: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9+.-]*://", value, flags=re.IGNORECASE))


def _search_query_variants(query: str) -> list[str]:
    variants = [query]
    lowered = query.lower()
    if "thasupreme" in lowered:
        variants.append(re.sub("thasupreme", "thasup", query, flags=re.IGNORECASE))
        variants.append(re.sub("thasupreme", "tha supreme", query, flags=re.IGNORECASE))
    if re.search(r"\bfuck ex\b", lowered):
        variants.extend(
            re.sub(r"\bfuck ex\b", "fuck 3x", variant, flags=re.IGNORECASE)
            for variant in list(variants)
        )
        variants.append("thasup fuck ex lyrics")
        variants.append("fuck ex tha supreme lyrics")
    return list(dict.fromkeys(variants))


def _iter_cookie_browsers(cookies_browser: str | Sequence[str] | None) -> Iterable[str | None]:
    if cookies_browser is None:
        yield None
        return

    browsers = (
        [part.strip() for part in cookies_browser.split(",")]
        if isinstance(cookies_browser, str)
        else list(cookies_browser)
    )
    for browser in browsers:
        if browser:
            yield browser


def download_mp3(
    query: str,
    output_dir: Path,
    archive_file: Path | None,
    ffmpeg_path: Path,
    quiet: bool = False,
    progress_hook: Callable[[dict[str, Any]], None] | None = None,
    js_runtime: JavascriptRuntime | None = None,
    cookies_browser: str | Sequence[str] | None = None,
) -> str:
    import yt_dlp

    if js_runtime is None:
        js_runtime = find_javascript_runtime()

    last_cookie_error: Exception | None = None
    for browser in _iter_cookie_browsers(cookies_browser):
        options = build_ydl_options(
            output_dir,
            archive_file,
            ffmpeg_path,
            quiet,
            progress_hook,
            js_runtime,
            browser,
        )
        try:
            if _looks_like_url(query):
                candidates = [query]
            else:
                candidates = []
                for search_query in _search_query_variants(query):
                    search_options = dict(options)
                    search_options["skip_download"] = True
                    search_options["extract_flat"] = "in_playlist"
                    with yt_dlp.YoutubeDL(search_options) as ydl:
                        search_info = ydl.extract_info(
                            f"ytsearch8:{search_query}", download=False
                        )
                    candidates.extend(
                        entry.get("webpage_url")
                        or f"https://www.youtube.com/watch?v={entry['id']}"
                        for entry in (search_info.get("entries") or [])
                        if entry and (entry.get("webpage_url") or entry.get("id"))
                    )
                candidates = list(dict.fromkeys(candidates))

            last_candidate_error: Exception | None = None
            for candidate in candidates:
                try:
                    with yt_dlp.YoutubeDL(options) as ydl:
                        info = ydl.extract_info(candidate, download=True)
                    break
                except Exception as candidate_exc:
                    if _is_age_or_login_error(candidate_exc):
                        last_candidate_error = candidate_exc
                        continue
                    raise
            else:
                if last_candidate_error is not None:
                    raise last_candidate_error
                raise RuntimeError("No downloadable result was found.")
            break
        except Exception as exc:
            if _is_cookie_load_error(exc):
                last_cookie_error = exc
                continue
            if not _is_forbidden_error(exc):
                raise

            fallback_options = dict(options)
            fallback_options["format"] = "bestaudio/best"
            fallback_options["extractor_args"] = {"youtube": {"player_client": ["android"]}}
            with yt_dlp.YoutubeDL(fallback_options) as ydl:
                info = ydl.extract_info(query, download=True)
            break
    else:
        assert last_cookie_error is not None
        raise last_cookie_error

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
    _ensure_utf8_console()
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

    if args.dry_run:
        for query in queries:
            print(f"  ytsearch1:{query}")
        return 0

    try:
        dependencies = check_dependencies()
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    completed_downloads = 0
    failed_downloads = 0

    for index, query in enumerate(queries, start=1):
        try:
            title = download_mp3(
                query,
                output_dir,
                archive_file,
                dependencies.ffmpeg_path,
                js_runtime=dependencies.javascript_runtime,
            )
            completed_downloads += 1
            print(f"[OK] {index}/{len(queries)} {query} -> {title}")
        except Exception as exc:
            failed_downloads += 1
            category, detail = classify_download_error(exc)
            print(
                f"[{category}] {index}/{len(queries)} {query}: {detail}",
                file=sys.stderr,
            )

    print(
        f"[INFO] Finished. Completed: {completed_downloads}. Failed: {failed_downloads}."
    )
    return 1 if failed_downloads else 0


if __name__ == "__main__":
    raise SystemExit(main())
