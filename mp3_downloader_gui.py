#!/usr/bin/env python3
"""
Simple desktop interface for MP3 Downloader.

The GUI lets users choose a song-list file, paste one or more direct YouTube
URLs, choose an output folder, and start downloads without typing command-line
arguments.
"""

from __future__ import annotations

import ctypes
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from mp3_download import (
    DEFAULT_INPUT_FILE,
    DEFAULT_OUTPUT_DIR,
    check_dependencies,
    download_mp3,
    get_download_title,
    load_queries,
    normalize_song_line,
)


SONG_LIST_WINDOW_SIZE = "760x650"
YOUTUBE_LINKS_WINDOW_SIZE = "760x620"
SONG_LIST_NOTEBOOK_HEIGHT = 250
YOUTUBE_LINKS_NOTEBOOK_HEIGHT = 220
SONG_LIST_LOG_HEIGHT = 10
YOUTUBE_LINKS_LOG_HEIGHT = 10
ICON_PATH = Path(__file__).resolve().parent / "Images" / "icon.png"


def load_queries_from_text(text: str) -> list[str]:
    queries: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        normalized = normalize_song_line(line)
        if normalized:
            queries.append(normalized)

    return queries



class Mp3DownloaderGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("MP3 Downloader")
        self.geometry(SONG_LIST_WINDOW_SIZE)
        self.resizable(False, False)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.logo_image: tk.PhotoImage | None = self._load_logo_image()

        self.input_file = tk.StringVar(value=str(Path(DEFAULT_INPUT_FILE).resolve()))
        self.output_dir = tk.StringVar(value=str(Path(DEFAULT_OUTPUT_DIR).resolve()))
        self.use_archive = tk.BooleanVar(value=True)

        self._build_layout()
        self._set_title_bar_color()
        self._poll_log_queue()

    def _set_title_bar_color(self) -> None:
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            caption_color = ctypes.c_int(0x00FFFFFF)
            text_color = ctypes.c_int(0x00000000)

            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                35,
                ctypes.byref(caption_color),
                ctypes.sizeof(caption_color),
            )
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                36,
                ctypes.byref(text_color),
                ctypes.sizeof(text_color),
            )
        except (AttributeError, OSError, tk.TclError):
            return

    def _load_logo_image(self) -> tk.PhotoImage | None:
        if not ICON_PATH.exists():
            return None

        try:
            logo = tk.PhotoImage(file=ICON_PATH)
            self.iconphoto(True, logo)
            scale = max(1, min(logo.width() // 42, logo.height() // 42))
            return logo.subsample(scale, scale)
        except tk.TclError:
            return None

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        main = ttk.Frame(self, padding=16)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(1, weight=1)

        if self.logo_image is not None:
            logo_label = ttk.Label(main, image=self.logo_image)
            logo_label.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 12))

        title = ttk.Label(main, text="MP3 Downloader", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=1, columnspan=2, sticky="w", pady=(0, 4))

        subtitle = ttk.Label(
            main,
            text="Download MP3 audio from a song list or direct YouTube links.",
        )
        subtitle.grid(row=1, column=1, columnspan=2, sticky="w", pady=(0, 16))

        ttk.Label(main, text="Output folder").grid(row=2, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.output_dir).grid(
            row=2, column=1, sticky="ew", padx=8
        )
        ttk.Button(main, text="Browse", command=self._choose_output_dir).grid(
            row=2, column=2, sticky="e"
        )

        archive_check = ttk.Checkbutton(
            main,
            text="Skip videos that were already downloaded",
            variable=self.use_archive,
        )
        archive_check.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.notebook.configure(height=SONG_LIST_NOTEBOOK_HEIGHT)
        self.notebook.columnconfigure(0, weight=1)
        self.notebook.bind("<<NotebookTabChanged>>", self._resize_for_selected_tab)

        list_tab = ttk.Frame(self.notebook, padding=16)
        list_tab.columnconfigure(1, weight=1)
        self.notebook.add(list_tab, text="Song list")

        ttk.Label(list_tab, text="Song-list file").grid(row=0, column=0, sticky="w")
        ttk.Entry(list_tab, textvariable=self.input_file).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        ttk.Button(list_tab, text="Browse", command=self._choose_input_file).grid(
            row=0, column=2, sticky="e"
        )

        ttk.Label(
            list_tab,
            text="Use a file, or write songs below. Manual entries are used first.",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 8))

        manual_songs_frame = ttk.Frame(list_tab)
        manual_songs_frame.grid(row=2, column=0, columnspan=3, sticky="nsew")
        manual_songs_frame.columnconfigure(0, weight=1)
        manual_songs_frame.rowconfigure(0, weight=1)
        list_tab.rowconfigure(2, weight=1)

        self.manual_songs_text = tk.Text(manual_songs_frame, height=5, wrap="word")
        self.manual_songs_text.grid(row=0, column=0, sticky="nsew")

        manual_songs_scrollbar = ttk.Scrollbar(
            manual_songs_frame,
            orient="vertical",
            command=self.manual_songs_text.yview,
        )
        manual_songs_scrollbar.grid(row=0, column=1, sticky="ns")
        self.manual_songs_text.configure(yscrollcommand=manual_songs_scrollbar.set)

        self.list_button = ttk.Button(
            list_tab,
            text="Download songs",
            command=self._download_from_file,
        )
        self.list_button.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(16, 0))

        link_tab = ttk.Frame(self.notebook, padding=16)
        link_tab.columnconfigure(1, weight=1)
        self.notebook.add(link_tab, text="YouTube links")

        ttk.Label(link_tab, text="YouTube URLs").grid(row=0, column=0, sticky="w")
        ttk.Label(link_tab, text="Paste one link per line.").grid(
            row=1, column=0, sticky="w", pady=(4, 8)
        )

        url_box_frame = ttk.Frame(link_tab)
        url_box_frame.grid(row=2, column=0, sticky="nsew")
        url_box_frame.columnconfigure(0, weight=1)
        url_box_frame.rowconfigure(0, weight=1)
        link_tab.rowconfigure(2, weight=1)

        self.youtube_urls_text = tk.Text(url_box_frame, height=7, wrap="word")
        self.youtube_urls_text.grid(row=0, column=0, sticky="nsew")

        url_scrollbar = ttk.Scrollbar(
            url_box_frame, orient="vertical", command=self.youtube_urls_text.yview
        )
        url_scrollbar.grid(row=0, column=1, sticky="ns")
        self.youtube_urls_text.configure(yscrollcommand=url_scrollbar.set)

        self.link_button = ttk.Button(
            link_tab,
            text="Download direct links",
            command=self._download_from_urls,
        )
        self.link_button.grid(row=3, column=0, sticky="ew", pady=(16, 0))

        log_frame = ttk.Frame(self, padding=(16, 0, 16, 16))
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)

        ttk.Label(log_frame, text="Activity log").grid(row=0, column=0, sticky="w")
        self.log_text = tk.Text(
            log_frame,
            height=SONG_LIST_LOG_HEIGHT,
            wrap="word",
            state="disabled",
        )
        self.log_text.grid(row=1, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text.yview
        )
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _resize_for_selected_tab(self, _event: tk.Event | None = None) -> None:
        selected_index = self.notebook.index(self.notebook.select())
        if selected_index == 1:
            self.geometry(YOUTUBE_LINKS_WINDOW_SIZE)
            self.notebook.configure(height=YOUTUBE_LINKS_NOTEBOOK_HEIGHT)
            self.log_text.configure(height=YOUTUBE_LINKS_LOG_HEIGHT)
        else:
            self.geometry(SONG_LIST_WINDOW_SIZE)
            self.notebook.configure(height=SONG_LIST_NOTEBOOK_HEIGHT)
            self.log_text.configure(height=SONG_LIST_LOG_HEIGHT)

    def _choose_input_file(self) -> None:
        selected_file = filedialog.askopenfilename(
            title="Choose song-list file",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
        )
        if selected_file:
            self.input_file.set(selected_file)

    def _choose_output_dir(self) -> None:
        selected_dir = filedialog.askdirectory(title="Choose output folder")
        if selected_dir:
            self.output_dir.set(selected_dir)

    def _download_from_file(self) -> None:
        manual_text = self.manual_songs_text.get("1.0", "end")
        manual_queries = load_queries_from_text(manual_text)
        input_file = Path(self.input_file.get()).expanduser()
        output_dir = Path(self.output_dir.get()).expanduser()
        use_archive = self.use_archive.get()

        if manual_queries:
            self._start_worker(
                lambda: self._run_manual_download(manual_queries, output_dir, use_archive),
            )
            return

        if not input_file.exists():
            messagebox.showerror("Missing file", "Choose a valid song-list file.")
            return

        self._start_worker(
            lambda: self._run_file_download(input_file, output_dir, use_archive),
        )

    def _run_manual_download(
        self, queries: list[str], output_dir: Path, use_archive: bool
    ) -> None:
        try:
            self._download_named_queries(queries, output_dir.resolve(), use_archive)
        except Exception as exc:
            self._log(f"ERROR: {exc}")
        finally:
            self._set_buttons_enabled(True)

    def _download_from_urls(self) -> None:
        raw_urls = self.youtube_urls_text.get("1.0", "end")
        urls = [line.strip() for line in raw_urls.splitlines() if line.strip()]
        output_dir = Path(self.output_dir.get()).expanduser()
        use_archive = self.use_archive.get()

        if not urls:
            messagebox.showerror(
                "Missing URLs",
                "Paste at least one YouTube URL, using one link per line.",
            )
            return

        self._start_worker(
            lambda: self._run_url_download(urls, output_dir, use_archive),
        )

    def _start_worker(self, target: Callable[[], None]) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo(
                "Download in progress",
                "Please wait for the current download to finish.",
            )
            return

        self._set_buttons_enabled(False)

        self.worker_thread = threading.Thread(target=target, daemon=True)
        self.worker_thread.start()

    def _run_file_download(
        self, input_file: Path, output_dir: Path, use_archive: bool
    ) -> None:
        try:
            queries = load_queries(input_file.resolve())
            if not queries:
                self._log("No songs found in the selected file.")
                return

            self._download_named_queries(queries, output_dir.resolve(), use_archive)
        except Exception as exc:
            self._log(f"ERROR: {exc}")
        finally:
            self._set_buttons_enabled(True)

    def _run_url_download(
        self, urls: list[str], output_dir: Path, use_archive: bool
    ) -> None:
        try:
            self._download_direct_urls(urls, output_dir.resolve(), use_archive)
        except Exception as exc:
            self._log(f"ERROR: {exc}")
        finally:
            self._set_buttons_enabled(True)

    def _download_named_queries(
        self, queries: list[str], output_dir: Path, use_archive: bool
    ) -> None:
        ffmpeg_path = check_dependencies()
        output_dir.mkdir(parents=True, exist_ok=True)
        archive_file = output_dir / "downloaded.txt" if use_archive else None

        for query in queries:
            try:
                progress_hook = self._make_progress_hook(query)
                title = download_mp3(
                    query,
                    output_dir,
                    archive_file,
                    ffmpeg_path,
                    quiet=True,
                    progress_hook=progress_hook,
                )
                self._log(f"Found: {query} -> {title}")
                self._log(f"Completed: {title}")
            except Exception as exc:
                self._log(f"{query} -> failed: {exc}")

    def _download_direct_urls(
        self, urls: list[str], output_dir: Path, use_archive: bool
    ) -> None:
        ffmpeg_path = check_dependencies()
        output_dir.mkdir(parents=True, exist_ok=True)
        archive_file = output_dir / "downloaded.txt" if use_archive else None

        for url in urls:
            try:
                progress_hook = self._make_progress_hook(url)
                title = download_mp3(
                    url,
                    output_dir,
                    archive_file,
                    ffmpeg_path,
                    quiet=True,
                    progress_hook=progress_hook,
                )
                self._log(f"Completed: {title}")
            except Exception as exc:
                self._log(f"{url} -> failed: {exc}")

    def _make_progress_hook(self, fallback_title: str) -> Callable[[dict], None]:
        last_eta_bucket: int | None = None
        last_title: str | None = None

        def progress_hook(progress: dict) -> None:
            nonlocal last_eta_bucket, last_title

            if progress.get("status") != "downloading":
                return

            title = get_download_title(progress.get("info_dict"), fallback_title)
            eta = progress.get("eta")
            eta_bucket = self._eta_bucket(eta)

            if title == last_title and eta_bucket == last_eta_bucket:
                return

            last_title = title
            last_eta_bucket = eta_bucket
            self._log(f"Downloading: {title} | ETA: {self._format_eta(eta)}")

        return progress_hook

    @staticmethod
    def _eta_bucket(eta: object) -> int:
        if not isinstance(eta, (int, float)) or eta < 0:
            return -1

        seconds = int(eta)
        if seconds < 60:
            return seconds // 5

        return seconds // 10

    @staticmethod
    def _format_eta(eta: object) -> str:
        if not isinstance(eta, (int, float)) or eta < 0:
            return "calculating"

        total_seconds = int(eta)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"

        return f"{minutes:02d}:{seconds:02d}"

    def _set_buttons_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.after(0, lambda: self.list_button.configure(state=state))
        self.after(0, lambda: self.link_button.configure(state=state))

    def _log(self, message: str) -> None:
        self.log_queue.put(message)

    def _poll_log_queue(self) -> None:
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break

            self.log_text.configure(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        self.after(100, self._poll_log_queue)


def main() -> int:
    app = Mp3DownloaderGui()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
