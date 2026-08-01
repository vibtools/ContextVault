from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.build.build_windows import (
    REQUIRED_DISTRIBUTION_PATHS,
    BuildConfigurationError,
    build_command,
    finalize_distribution,
    load_configuration,
    run_build,
)
from scripts.release.package_release import REQUIRED_DISTRIBUTION_PATHS as PACKAGE_REQUIRED_PATHS


ROOT = Path(__file__).resolve().parents[1]


class ReleaseBuildPipelineTests(unittest.TestCase):
    def test_release_build_sources_are_visible_while_outputs_remain_ignored(self) -> None:
        git = shutil.which("git")
        if git is None:
            self.skipTest("Git is required for ignore-policy regression coverage.")

        for relative in (
            "scripts/build/README.md",
            "scripts/build/build_windows.py",
        ):
            with self.subTest(source=relative):
                result = subprocess.run(
                    [git, "-C", str(ROOT), "check-ignore", "--quiet", "--no-index", relative],
                    check=False,
                )
                self.assertEqual(
                    result.returncode,
                    1,
                    f"Release build source is incorrectly ignored: {relative}",
                )

        for relative in (
            "build/generated.bin",
            "dist/generated.bin",
            "artifacts/generated.bin",
            "scripts/build/__pycache__/build_windows.cpython-312.pyc",
            "scripts/build/transient.dist/generated.bin",
        ):
            with self.subTest(output=relative):
                result = subprocess.run(
                    [git, "-C", str(ROOT), "check-ignore", "--quiet", "--no-index", relative],
                    check=False,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"Generated release output is not ignored: {relative}",
                )

    def test_release_workflow_python_script_references_exist(self) -> None:
        workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        references = {
            match.replace("\\", "/")
            for match in re.findall(r"\bpython\s+(scripts[\\/][A-Za-z0-9_.+\\/-]+\.py)\b", workflow)
        }
        self.assertIn("scripts/build/build_windows.py", references)
        missing = sorted(reference for reference in references if not (ROOT / reference).is_file())
        self.assertEqual(missing, [])

    def test_official_configuration_generates_expected_command(self) -> None:
        configuration = load_configuration(ROOT)
        command = build_command(configuration, ROOT, python_executable=ROOT / ".venv-release/Scripts/python.exe")
        joined = "\n".join(command)
        self.assertEqual(command[1:3], ["-m", "nuitka"])
        self.assertIn("--mode=standalone", command)
        self.assertIn("--msvc=latest", command)
        self.assertIn("--windows-console-mode=disable", command)
        self.assertIn("--output-filename=ContextVault", command)
        self.assertIn("--include-package-data=customtkinter", command)
        self.assertTrue(configuration.assume_yes_for_downloads)
        self.assertIn("--assume-yes-for-downloads", command)
        self.assertEqual(Path(command[-1]).resolve(), (ROOT / "src/app.py").resolve())
        self.assertIn("runtime/assets", joined)
        self.assertIn("runtime/config", joined)
        self.assertIn("runtime/schemas", joined)
        self.assertIn("README.txt", joined)
        self.assertIn("LICENSE", joined)

    def test_build_and_packaging_required_paths_are_identical(self) -> None:
        self.assertEqual(REQUIRED_DISTRIBUTION_PATHS, PACKAGE_REQUIRED_PATHS)

    def test_finalize_distribution_creates_writable_directories_and_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_minimal_repository(root)
            configuration = load_configuration(root)
            distribution = root / "build" / "app.dist"
            distribution.mkdir(parents=True)
            for relative in (
                "runtime/assets",
                "runtime/config",
                "runtime/icons",
                "runtime/schemas",
                "runtime/templates",
                "runtime/themes",
            ):
                (distribution / relative).mkdir(parents=True)
            (distribution / "ContextVault.exe").write_bytes(b"MZ-test")
            (distribution / "README.txt").write_text("readme\n", encoding="utf-8")
            (distribution / "LICENSE").write_text("license\n", encoding="utf-8")

            result = finalize_distribution(configuration, root)

            self.assertEqual(result, distribution.resolve())
            for relative in ("data", "exports", "logs"):
                self.assertTrue((distribution / relative).is_dir())
            marker = root / "build" / "distribution-path.txt"
            self.assertEqual(marker.read_text(encoding="utf-8").strip(), str(distribution.resolve()))


    def test_run_build_orchestrates_clean_compile_and_finalize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_minimal_repository(root)
            stale = root / "build" / "stale.txt"
            stale.write_text("stale\n", encoding="utf-8")

            def fake_compile(command: list[str], *, cwd: Path, check: bool) -> None:
                self.assertTrue(check)
                self.assertTrue(
                    os.path.samefile(cwd, root),
                    f"Build cwd {cwd!s} does not identify repository root {root!s}.",
                )
                self.assertFalse(stale.exists())
                self.assertIn("--mode=standalone", command)
                distribution = root / "build" / "app.dist"
                for relative in (
                    "runtime/assets",
                    "runtime/config",
                    "runtime/icons",
                    "runtime/schemas",
                    "runtime/templates",
                    "runtime/themes",
                ):
                    (distribution / relative).mkdir(parents=True, exist_ok=True)
                (distribution / "ContextVault.exe").write_bytes(b"MZ-test")
                (distribution / "README.txt").write_text("readme\n", encoding="utf-8")
                (distribution / "LICENSE").write_text("license\n", encoding="utf-8")

            with (
                patch("scripts.build.build_windows.verify_build_runtime"),
                patch("scripts.build.build_windows.subprocess.run", side_effect=fake_compile) as mocked_run,
            ):
                distribution = run_build(root)

            self.assertEqual(distribution, (root / "build" / "app.dist").resolve())
            mocked_run.assert_called_once()
            self.assertTrue((root / "build" / "nuitka-command.txt").is_file())
            self.assertTrue((root / "build" / "distribution-path.txt").is_file())

    def test_configuration_rejects_missing_data_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_minimal_repository(root)
            config = (root / "nuitka.toml").read_text(encoding="utf-8")
            config = config.replace("assets=runtime/assets", "missing-assets=runtime/assets")
            (root / "nuitka.toml").write_text(config, encoding="utf-8")
            with self.assertRaisesRegex(BuildConfigurationError, "does not exist"):
                load_configuration(root)

    @staticmethod
    def _write_minimal_repository(root: Path) -> None:
        for relative in (
            "src",
            "assets/icons",
            "assets/themes",
            "config/schemas",
            "data/templates",
            "build",
        ):
            (root / relative).mkdir(parents=True, exist_ok=True)
        (root / "src/app.py").write_text("print('test')\n", encoding="utf-8")
        (root / "assets/icons/app.ico").write_bytes(b"ico")
        (root / "assets/themes/theme.json").write_text("{}\n", encoding="utf-8")
        (root / "assets/asset.txt").write_text("asset\n", encoding="utf-8")
        (root / "config/defaults.json").write_text("{}\n", encoding="utf-8")
        (root / "config/schemas/test.json").write_text("{}\n", encoding="utf-8")
        (root / "data/templates/README.txt").write_text("template\n", encoding="utf-8")
        (root / "README.txt").write_text("readme\n", encoding="utf-8")
        (root / "LICENSE").write_text("license\n", encoding="utf-8")
        (root / "requirements-build.lock").write_text("Nuitka==4.1.3\n", encoding="utf-8")
        source_config = (ROOT / "nuitka.toml").read_text(encoding="utf-8")
        (root / "nuitka.toml").write_text(source_config, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
