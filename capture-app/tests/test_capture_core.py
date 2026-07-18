from datetime import datetime
from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from capture_core import build_capture_paths  # noqa: E402


class CaptureCoreTests(unittest.TestCase):
    def test_build_capture_paths_one_page(self) -> None:
        output_dir = Path("/tmp/capture")
        paths = build_capture_paths(output_dir, "one_page", now=datetime(2026, 7, 18, 10, 30, 15, 123000))
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].name, "20260718-103015-123.jpg")

    def test_build_capture_paths_two_pages(self) -> None:
        output_dir = Path("/tmp/capture")
        paths = build_capture_paths(output_dir, "two_pages", now=datetime(2026, 7, 18, 10, 30, 15, 123000))
        self.assertEqual(len(paths), 2)
        self.assertTrue(paths[0].name.endswith("-left.jpg"))
        self.assertTrue(paths[1].name.endswith("-right.jpg"))

if __name__ == "__main__":
    unittest.main()


