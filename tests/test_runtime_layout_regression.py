from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.build.build_windows import (
    REQUIRED_DISTRIBUTION_PATHS as BUILD_REQUIRED_PATHS,
)
from scripts.release.package_release import (
    REQUIRED_DISTRIBUTION_PATHS as PACKAGE_REQUIRED_PATHS,
)
from src.models.settings import ApplicationSettings
from src.services.config_service import ConfigService
from src.utils.paths import (
    PORTABLE_RUNTIME_MARKERS,
    application_root,
    portable_runtime_missing_paths,
)


class RuntimeLayoutRegressionTests(unittest.TestCase):
    def test_compiled_root_falls_back_to_executable_root_when_runtime_is_there(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            incorrect_compiled_root = base / "incorrect"
            executable_root = base / "ContextVault"
            incorrect_compiled_root.mkdir()
            executable_root.mkdir()
            for relative in PORTABLE_RUNTIME_MARKERS:
                path = executable_root / relative
                if Path(relative).suffix:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("{}\n", encoding="utf-8")
                else:
                    path.mkdir(parents=True, exist_ok=True)
            executable = executable_root / "ContextVault.exe"
            executable.write_bytes(b"MZ")

            with (
                patch(
                    "src.utils.paths.__compiled__",
                    SimpleNamespace(containing_dir=str(incorrect_compiled_root)),
                    create=True,
                ),
                patch.object(sys, "executable", str(executable)),
            ):
                self.assertEqual(application_root(), executable_root.resolve())

    def test_missing_runtime_markers_are_reported_without_creating_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = portable_runtime_missing_paths(root)
            self.assertEqual(missing, PORTABLE_RUNTIME_MARKERS)
            self.assertEqual(list(root.iterdir()), [])

    def test_missing_shipped_defaults_use_embedded_defaults_with_actionable_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "data" / "settings.json"
            service = ConfigService(settings_path)

            with (
                patch(
                    "src.services.config_service.configuration_path",
                    return_value=Path(directory) / "runtime/config/defaults.json",
                ),
                patch(
                    "src.services.config_service.portable_runtime_missing_paths",
                    return_value=("runtime/config/defaults.json",),
                ),
                self.assertLogs(
                    "src.services.config_service",
                    level="WARNING",
                ) as captured,
            ):
                settings = service.load()

            self.assertEqual(settings, ApplicationSettings())
            self.assertTrue(settings_path.is_file())
            text = "\n".join(captured.output)
            self.assertIn("using embedded safe model defaults", text)
            self.assertIn("runtime/config/defaults.json", text)
            self.assertNotIn("ERROR", text)

    def test_build_and_package_require_the_defaults_file_not_only_the_directory(self) -> None:
        self.assertEqual(BUILD_REQUIRED_PATHS, PACKAGE_REQUIRED_PATHS)
        self.assertIn("runtime/config/defaults.json", BUILD_REQUIRED_PATHS)


if __name__ == "__main__":
    unittest.main()
