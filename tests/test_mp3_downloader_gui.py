from __future__ import annotations

import unittest

import mp3_downloader_gui


class GuiQueryLoadingTests(unittest.TestCase):
    def test_load_queries_from_text_normalizes_manual_songs(self) -> None:
        self.assertEqual(
            mp3_downloader_gui.load_queries_from_text(
                "# ignore\n\nArtist; Title\nOther | Song\nPlain - Track\n"
            ),
            ["Artist - Title", "Other - Song", "Plain - Track"],
        )

    def test_wordmark_uses_mp3_downloader_only(self) -> None:
        self.assertIn("____   _____", mp3_downloader_gui.WORDMARK)
        self.assertNotIn("MP3 Downloader", mp3_downloader_gui.WORDMARK)

    def test_progress_bar_is_ascii_percent(self) -> None:
        self.assertEqual(
            mp3_downloader_gui.Mp3DownloaderGui._progress_bar(50),
            "[############............]  50%",
        )

    def test_progress_percent_uses_downloaded_and_total_bytes(self) -> None:
        self.assertEqual(
            mp3_downloader_gui.Mp3DownloaderGui._progress_percent(
                {"downloaded_bytes": 25, "total_bytes": 100}
            ),
            25.0,
        )


if __name__ == "__main__":
    unittest.main()
