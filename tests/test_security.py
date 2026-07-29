from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.utils.security import ensure_within_root, sanitize_filename, validate_relative_archive_path


class SecurityTests(unittest.TestCase):
    def test_sanitize_windows_filename(self) -> None:
        self.assertEqual(sanitize_filename('bad<name>:file?.txt'), "bad_name__file_.txt")
        self.assertEqual(sanitize_filename("CON"), "_CON")

    def test_rejects_archive_traversal_and_backslashes(self) -> None:
        for value in ("../secret", "/absolute", "assets\\file.txt"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_relative_archive_path(value)

    def test_sanitize_respects_strict_maximum_length(self) -> None:
        value = "name." + ("x" * 200)
        self.assertLessEqual(len(sanitize_filename(value, max_length=16)), 16)
        with self.assertRaises(ValueError):
            sanitize_filename("name", max_length=0)

    def test_ensure_within_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            child = root / "child.txt"
            self.assertEqual(ensure_within_root(child, root), child)
            with self.assertRaises(ValueError):
                ensure_within_root(root.parent / "escape.txt", root)


class BrowserSettingsSecurityTests(unittest.TestCase):
    def test_profile_directory_rejects_cross_platform_paths(self) -> None:
        from pydantic import ValidationError
        from src.models.settings import BrowserSettings

        for value in ("../Default", r"..\\Default", "profiles/Default", r"profiles\\Default", ".", ".."):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                BrowserSettings(profileDirectory=value)

if __name__ == "__main__":
    unittest.main()
