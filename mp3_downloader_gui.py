#!/usr/bin/env python3
"""Tk desktop GUI styled from DESIGN.md."""

from __future__ import annotations

import ctypes
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

from mp3_download import (
    DEFAULT_INPUT_FILE,
    DEFAULT_OUTPUT_DIR,
    check_dependencies,
    classify_download_error,
    download_mp3,
    get_download_title,
    load_queries,
    normalize_song_line,
)


WINDOW_SIZE = "760x700"
SOURCE_PANEL_HEIGHT = 150
ICON_PATH = Path(__file__).resolve().parent / "Images" / "icon.png"
BUTTON_WIDTH = 18
CONTROL_HEIGHT = 26
CONTROL_PADY = 3

CANVAS = "#fdfcfc"
SOFT = "#f8f7f7"
INK = "#201d1d"
BODY = "#424245"
MUTE = "#646262"
HAIRLINE = "#e3dede"
DARK = "#201d1d"
DARK_ELEVATED = "#302c2c"
ON_DARK = "#fdfcfc"
ASH = "#9a9898"
SUCCESS = "#30d158"
DANGER = "#ff3b30"
BAR_WIDTH = 24

WORDMARK = r"""
 __  __ ____ _____   ____   _____        ___   _ _     ___    _    ____  _____ ____
|  \/  |  _ \___ /  |  _ \ / _ \ \      / / \ | | |   / _ \  / \  |  _ \| ____|  _ \
| |\/| | |_) ||_ \  | | | | | | \ \ /\ / /|  \| | |  | | | |/ _ \ | | | |  _| | |_) |
| |  | |  __/___) | | |_| | |_| |\ V  V / | |\  | |__| |_| / ___ \| |_| | |___|  _ <
|_|  |_|_|  |____/  |____/ \___/  \_/\_/  |_| \_|_____\___/_/   \_\____/|_____|_| \_\
""".strip("\n")


def _mono_font(root: tk.Tk) -> str:
    import tkinter.font as tkfont

    families = set(tkfont.families(root))
    for candidate in ("Berkeley Mono", "JetBrains Mono", "Consolas", "Courier New"):
        if candidate in families:
            return candidate
    return "TkFixedFont"


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

        self.title("mp3-downloader")
        self.geometry(WINDOW_SIZE)
        self.minsize(680, 620)
        self.configure(bg=CANVAS)

        self.mono = _mono_font(self)
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.ui_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.logo_image: tk.PhotoImage | None = self._load_logo_image()

        self.input_file = tk.StringVar(value=str(Path(DEFAULT_INPUT_FILE).resolve()))
        self.output_dir = tk.StringVar(value=str(Path(DEFAULT_OUTPUT_DIR).resolve()))
        self.use_archive = tk.BooleanVar(value=True)
        self.mode = tk.StringVar(value="songs")

        self._build_layout()
        self._set_title_bar_color()
        self._poll_log_queue()

    def _set_title_bar_color(self) -> None:
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            caption_color = ctypes.c_int(0x00FCFCFD)
            text_color = ctypes.c_int(0x001D1D20)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color)
            )
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 36, ctypes.byref(text_color), ctypes.sizeof(text_color)
            )
        except (AttributeError, OSError, tk.TclError):
            return

    def _load_logo_image(self) -> tk.PhotoImage | None:
        if not ICON_PATH.exists():
            return None
        try:
            logo = tk.PhotoImage(file=ICON_PATH)
            self.iconphoto(True, logo)
            return logo
        except tk.TclError:
            return None

    def _label(self, parent: tk.Widget, text: str, fg: str = BODY, bold: bool = False) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            bg=CANVAS,
            fg=fg,
            font=(self.mono, 10, "bold" if bold else "normal"),
            anchor="w",
            justify="left",
        )

    def _button(
        self,
        parent: tk.Widget,
        text: str,
        primary: bool,
        command: Callable[[], None],
        width: int | None = BUTTON_WIDTH,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=INK if primary else CANVAS,
            fg=CANVAS if primary else INK,
            disabledforeground=ASH,
            activebackground=DARK_ELEVATED if primary else SOFT,
            activeforeground=CANVAS if primary else INK,
            font=(self.mono, 10),
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            width=width or 0,
            padx=20,
            pady=CONTROL_PADY,
            cursor="hand2",
        )

    def _build_layout(self) -> None:
        root = tk.Frame(self, bg=CANVAS, padx=24, pady=16)
        root.pack(fill="both", expand=True)

        tk.Label(
            root,
            text=WORDMARK,
            bg=CANVAS,
            fg=INK,
            font=(self.mono, 6),
            anchor="w",
            justify="left",
        ).pack(fill="x")

        self._label(
            root,
            "scarica audio mp3 da brani o link youtube. niente fronzoli.",
            fg=MUTE,
        ).pack(fill="x", pady=(12, 0))

        tk.Frame(root, bg=HAIRLINE, height=1).pack(fill="x", pady=16)

        self._label(root, "[+] sorgente", fg=INK, bold=True).pack(fill="x")
        mode_row = tk.Frame(root, bg=CANVAS)
        mode_row.pack(fill="x", pady=(6, 8))
        self.songs_mode_button = self._button(
            mode_row,
            "[brani]",
            primary=True,
            command=lambda: self._set_mode("songs"),
            width=BUTTON_WIDTH,
        )
        self.songs_mode_button.pack(side="left")
        self.links_mode_button = self._button(
            mode_row,
            "[link]",
            primary=False,
            command=lambda: self._set_mode("links"),
            width=BUTTON_WIDTH,
        )
        self.links_mode_button.pack(side="left", padx=(8, 0))

        self.source_stack = tk.Frame(root, bg=CANVAS, height=SOURCE_PANEL_HEIGHT)
        self.source_stack.pack(fill="x")
        self.source_stack.pack_propagate(False)

        self.songs_panel = tk.Frame(self.source_stack, bg=CANVAS)
        self.links_panel = tk.Frame(self.source_stack, bg=CANVAS)
        self._build_songs_panel(self.songs_panel)
        self._build_links_panel(self.links_panel)
        self.songs_panel.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.links_panel.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.songs_panel.tkraise()

        self._label(root, "[+] cartella output", fg=INK, bold=True).pack(
            fill="x", pady=(16, 0)
        )
        out_row = tk.Frame(root, bg=CANVAS)
        out_row.pack(fill="x", pady=(6, 0))
        self.output_dir_button = self._button(
            out_row,
            "[scegli cartella]",
            primary=False,
            command=self._choose_output_dir,
            width=BUTTON_WIDTH,
        )
        self.output_dir_button.pack(side="left")
        self.output_entry_frame = tk.Frame(
            out_row,
            bg=CANVAS,
            height=CONTROL_HEIGHT,
        )
        self.output_entry_frame.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.output_entry_frame.pack_propagate(False)
        self.output_dir_entry = tk.Entry(
            self.output_entry_frame,
            textvariable=self.output_dir,
            bg=SOFT,
            fg=INK,
            insertbackground=INK,
            font=(self.mono, 10),
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightcolor=INK,
            highlightbackground=HAIRLINE,
        )
        self.output_dir_entry.pack(fill="both", expand=True)

        archive_row = tk.Frame(root, bg=CANVAS)
        archive_row.pack(fill="x", pady=(10, 0))
        tk.Checkbutton(
            archive_row,
            text="[x] salta gia scaricati",
            variable=self.use_archive,
            bg=CANVAS,
            fg=BODY,
            activebackground=CANVAS,
            activeforeground=INK,
            selectcolor=CANVAS,
            font=(self.mono, 10),
            relief="flat",
            highlightthickness=0,
            anchor="w",
        ).pack(side="left")

        btn_row = tk.Frame(root, bg=CANVAS)
        btn_row.pack(fill="x", pady=(16, 0))
        self.download_button = self._button(
            btn_row, "[scarica mp3]", primary=True, command=self._download
        )
        self.download_button.pack(side="left")

        self._label(root, "[x] log", fg=INK, bold=True).pack(fill="x", pady=(16, 0))
        self.log_text = tk.Text(
            root,
            height=12,
            bg=DARK,
            fg=ON_DARK,
            insertbackground=ON_DARK,
            font=(self.mono, 10),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=12,
            pady=8,
            wrap="word",
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True, pady=(6, 0))

    def _build_songs_panel(self, parent: tk.Frame) -> None:
        self._label(parent, "uno per riga. manuale prima del file.", fg=MUTE).pack(
            fill="x", pady=(0, 6)
        )
        self.manual_songs_text = self._text_box(parent, height=4)
        self.manual_songs_text.pack(fill="x")

        file_row = tk.Frame(parent, bg=CANVAS)
        file_row.pack(fill="x", pady=(8, 0))
        self.input_file_button = self._button(
            file_row,
            "[scegli file]",
            primary=False,
            command=self._choose_input_file,
            width=BUTTON_WIDTH,
        )
        self.input_file_button.pack(side="left")

    def _build_links_panel(self, parent: tk.Frame) -> None:
        self._label(parent, "un link youtube per riga.", fg=MUTE).pack(
            fill="x", pady=(0, 6)
        )
        self.youtube_urls_text = self._text_box(parent, height=4)
        self.youtube_urls_text.pack(fill="x")

    def _text_box(self, parent: tk.Widget, height: int) -> tk.Text:
        return tk.Text(
            parent,
            height=height,
            bg=SOFT,
            fg=INK,
            insertbackground=INK,
            font=(self.mono, 10),
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightcolor=INK,
            highlightbackground=HAIRLINE,
            padx=12,
            pady=8,
            wrap="word",
        )

    def _set_mode(self, mode: str) -> None:
        self.mode.set(mode)
        if mode == "links":
            self.links_panel.tkraise()
        else:
            self.songs_panel.tkraise()
        self.songs_mode_button.configure(
            bg=INK if mode == "songs" else CANVAS,
            fg=CANVAS if mode == "songs" else INK,
            relief="flat" if mode == "songs" else "solid",
            borderwidth=0 if mode == "songs" else 1,
        )
        self.links_mode_button.configure(
            bg=INK if mode == "links" else CANVAS,
            fg=CANVAS if mode == "links" else INK,
            relief="flat" if mode == "links" else "solid",
            borderwidth=0 if mode == "links" else 1,
        )

    def _choose_input_file(self) -> None:
        selected_file = filedialog.askopenfilename(
            title="scegli lista brani",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
        )
        if selected_file:
            self.input_file.set(selected_file)
            messagebox.showinfo(
                "file scelto",
                f"file canzoni:\n{selected_file}",
            )

    def _choose_output_dir(self) -> None:
        selected_dir = filedialog.askdirectory(title="scegli cartella output")
        if selected_dir:
            self.output_dir.set(selected_dir)
            messagebox.showinfo(
                "cartella scelta",
                f"cartella output:\n{selected_dir}",
            )

    def _queries_for_mode(self) -> list[str]:
        if self.mode.get() == "links":
            return [
                line.strip()
                for line in self.youtube_urls_text.get("1.0", "end").splitlines()
                if line.strip()
            ]

        manual_queries = load_queries_from_text(self.manual_songs_text.get("1.0", "end"))
        if manual_queries:
            return manual_queries

        input_file = Path(self.input_file.get()).expanduser()
        if not input_file.exists():
            raise FileNotFoundError(f"file non trovato: {input_file}")
        return load_queries(input_file)

    def _download(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("download in corso", "attendi fine download.")
            return

        try:
            queries = self._queries_for_mode()
        except OSError as exc:
            self._log(f"[!] {exc}", DANGER)
            return

        if not queries:
            self._log("[!] niente brani.", DANGER)
            return

        output_dir = Path(self.output_dir.get()).expanduser()
        archive_file = output_dir / "downloaded.txt" if self.use_archive.get() else None
        cookies_browser = None
        self._set_buttons_enabled(False)
        self.worker_thread = threading.Thread(
            target=self._run_download,
            args=(queries, output_dir, archive_file, cookies_browser),
            daemon=True,
        )
        self.worker_thread.start()

    def _run_download(
        self,
        queries: list[str],
        output_dir: Path,
        archive_file: Path | None,
        cookies_browser: str | None,
    ) -> None:
        try:
            dependencies = check_dependencies()
            output_dir.mkdir(parents=True, exist_ok=True)

            for query in queries:
                try:
                    progress_hook = self._make_progress_hook(query)
                    self._log(f"[+] {query}", ON_DARK)
                    title = download_mp3(
                        query,
                        output_dir,
                        archive_file,
                        dependencies.ffmpeg_path,
                        quiet=True,
                        progress_hook=progress_hook,
                        js_runtime=dependencies.javascript_runtime,
                        cookies_browser=cookies_browser,
                    )
                    self._log(f"[ok] {title}", SUCCESS)
                except Exception as exc:
                    category, detail = classify_download_error(exc)
                    self._log(f"[x] {query} -> {category}: {detail}", DANGER)
        except Exception as exc:
            self._log(f"[!] {exc}", DANGER)
        finally:
            self._set_buttons_enabled(True)

    def _make_progress_hook(self, fallback_title: str) -> Callable[[dict], None]:
        last_percent_bucket: int | None = None
        last_title: str | None = None

        def progress_hook(progress: dict) -> None:
            nonlocal last_percent_bucket, last_title
            if progress.get("status") != "downloading":
                return

            title = get_download_title(progress.get("info_dict"), fallback_title)
            percent = self._progress_percent(progress)
            percent_bucket = int(percent // 5)
            if title == last_title and percent_bucket == last_percent_bucket:
                return

            last_title = title
            last_percent_bucket = percent_bucket
            self._log(f"{self._progress_bar(percent)} {title}", ON_DARK)

        return progress_hook

    @staticmethod
    def _progress_percent(progress: dict) -> float:
        total = progress.get("total_bytes") or progress.get("total_bytes_estimate")
        downloaded = progress.get("downloaded_bytes")
        if not isinstance(total, (int, float)) or total <= 0:
            return 0.0
        if not isinstance(downloaded, (int, float)) or downloaded < 0:
            return 0.0
        return max(0.0, min(100.0, (downloaded / total) * 100))

    @staticmethod
    def _progress_bar(percent: float) -> str:
        filled = int(round((percent / 100) * BAR_WIDTH))
        empty = BAR_WIDTH - filled
        return f"[{'#' * filled}{'.' * empty}] {percent:3.0f}%"

    def _set_buttons_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"

        def apply_state() -> None:
            self.download_button.configure(state=state)

        if threading.current_thread() is threading.main_thread():
            apply_state()
        else:
            self.ui_queue.put(apply_state)

    def _log(self, message: str, color: str = ON_DARK) -> None:
        self.log_queue.put((message, color))

    def _poll_log_queue(self) -> None:
        while True:
            try:
                ui_action = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            ui_action()

        while True:
            try:
                message, color = self.log_queue.get_nowait()
            except queue.Empty:
                break
            tag = f"c_{color}"
            self.log_text.configure(state="normal")
            if tag not in self.log_text.tag_names():
                self.log_text.tag_configure(tag, foreground=color)
            self.log_text.insert("end", message + "\n", tag)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(100, self._poll_log_queue)


def main() -> int:
    app = Mp3DownloaderGui()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
