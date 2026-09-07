from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import mp3_download


class QueryLoadingTests(unittest.TestCase):
    def test_load_queries_normalizes_supported_separators(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "songs.txt"
            input_file.write_text(
                "\n".join(
                    [
                        "# ignored",
                        "",
                        "Artist; Title",
                        "Other | Song",
                        "Plain Artist - Plain Title",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                mp3_download.load_queries(input_file),
                [
                    "Artist - Title",
                    "Other - Song",
                    "Plain Artist - Plain Title",
                ],
            )


class ErrorHandlingTests(unittest.TestCase):
    def test_classify_javascript_runtime_error(self) -> None:
        category, detail = mp3_download.classify_download_error(
            RuntimeError("No supported JavaScript runtime could be found")
        )

        self.assertEqual(category, "JAVASCRIPT RUNTIME ERROR")
        self.assertIn("JavaScript runtime", detail)

    def test_short_error_uses_first_non_empty_line(self) -> None:
        self.assertEqual(
            mp3_download.short_error(RuntimeError("\nfirst line\nsecond line")),
            "first line",
        )


class RuntimeOptionTests(unittest.TestCase):
    def test_build_ydl_options_sets_js_runtime_and_ejs_policy(self) -> None:
        runtime = mp3_download.JavascriptRuntime(
            "node",
            Path(r"C:\Program Files\nodejs\node.exe"),
            "24.18.0",
        )

        options = mp3_download.build_ydl_options(
            Path("downloads"),
            Path("downloads/downloaded.txt"),
            Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
            quiet=True,
            progress_hook=None,
            js_runtime=runtime,
        )

        self.assertEqual(
            options["js_runtimes"],
            {"node": {"path": r"C:\Program Files\nodejs\node.exe"}},
        )
        self.assertEqual(options["remote_components"], [])
        self.assertEqual(options["ffmpeg_location"], r"C:\ffmpeg\bin")
        self.assertEqual(options["download_archive"], "downloads\\downloaded.txt")
        self.assertEqual(options["source_address"], "0.0.0.0")
        self.assertEqual(options["retries"], 3)
        self.assertEqual(options["fragment_retries"], 3)

    @mock.patch.dict(
        os.environ,
        {
            "MP3_DOWNLOADER_JS_RUNTIME": "node",
            "MP3_DOWNLOADER_NODE_PATH": r"C:\Program Files\nodejs\node.exe",
        },
    )
    @mock.patch("mp3_download._safe_exists", return_value=False)
    @mock.patch("mp3_download._check_executable_output", return_value="v24.18.0")
    def test_find_javascript_runtime_uses_configured_node(
        self,
        _check_output: mock.Mock,
        _safe_exists: mock.Mock,
    ) -> None:
        runtime = mp3_download.find_javascript_runtime()

        self.assertIsNotNone(runtime)
        assert runtime is not None
        self.assertEqual(runtime.name, "node")
        self.assertEqual(runtime.version, "24.18.0")

    @mock.patch.dict(
        os.environ,
        {
            "MP3_DOWNLOADER_JS_RUNTIME": "node",
            "MP3_DOWNLOADER_NODE_PATH": r"C:\Program Files\nodejs\node.exe",
        },
    )
    @mock.patch("mp3_download._safe_exists", return_value=False)
    @mock.patch("mp3_download._check_executable_output")
    def test_find_javascript_runtime_rejects_old_node(
        self,
        check_output: mock.Mock,
        _safe_exists: mock.Mock,
    ) -> None:
        def fake_output(path: Path, _args: tuple[str, ...]) -> str | None:
            return "v20.19.2" if "node" in str(path).lower() else None

        check_output.side_effect = fake_output

        self.assertIsNone(mp3_download.find_javascript_runtime())


class FfmpegDiscoveryTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "WinGet fallback is Windows-only")
    @mock.patch("mp3_download._is_usable_executable", return_value=False)
    @mock.patch("mp3_download._iter_ffmpeg_candidates")
    def test_find_ffmpeg_trusts_winget_package_layout(
        self,
        iter_candidates: mock.Mock,
        _is_usable: mock.Mock,
    ) -> None:
        candidate = Path(
            r"C:\Users\me\AppData\Local\Microsoft\WinGet\Packages"
            r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
            r"\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
        )
        iter_candidates.return_value = [candidate]

        self.assertEqual(mp3_download.find_ffmpeg(), candidate)


if __name__ == "__main__":
    unittest.main()
