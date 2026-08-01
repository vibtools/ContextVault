from __future__ import annotations

import ast
import json
import tomllib
import unittest
from pathlib import Path

from scripts.release.verify_release_metadata import verify_release_metadata


ROOT = Path(__file__).resolve().parents[1]


class RepositoryIntegrityTests(unittest.TestCase):
    def test_all_json_and_toml_files_parse(self) -> None:
        for path in sorted(ROOT.rglob("*.json")):
            if any(part in {"build", "exports", "logs"} for part in path.parts):
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                json.loads(path.read_text(encoding="utf-8"))
        for path in (ROOT / "pyproject.toml", ROOT / "nuitka.toml"):
            with self.subTest(path=path.name):
                with path.open("rb") as stream:
                    tomllib.load(stream)

    def test_python_files_have_valid_ast(self) -> None:
        for base in (ROOT / "src", ROOT / "scripts", ROOT / "tests"):
            for path in sorted(base.rglob("*.py")):
                with self.subTest(path=path.relative_to(ROOT)):
                    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_ui_does_not_import_browser_implementation(self) -> None:
        for path in sorted((ROOT / "src/ui").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.append(node.module)
            self.assertFalse(
                any(name.startswith("src.browser") for name in imported),
                f"UI layer imports browser implementation: {path}",
            )


    def test_dependency_versions_are_synchronized(self) -> None:
        locked = {}
        for line in (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines():
            clean = line.strip()
            if clean and not clean.startswith("#"):
                name, version = clean.split("==", 1)
                locked[name.lower()] = version
        with (ROOT / "pyproject.toml").open("rb") as stream:
            dependencies = tomllib.load(stream)["project"]["dependencies"]
        metadata = {}
        for dependency in dependencies:
            name, version = dependency.split("==", 1)
            metadata[name.lower()] = version
        self.assertEqual(metadata, locked)
        self.assertEqual(verify_release_metadata(), [])

        expected_header = "ContextVault v0.2.1"
        for relative in ("requirements.txt", "requirements.lock", "requirements-build.lock"):
            with self.subTest(relative=relative):
                self.assertIn(expected_header, (ROOT / relative).read_text(encoding="utf-8"))

        verifier = (ROOT / "scripts/release/verify_release_candidate.py").read_text(encoding="utf-8")
        self.assertIn('DEFAULT_VENV = ROOT / ".venv-release"', verifier)
        self.assertIn('"requirements.lock"', verifier)
        self.assertIn('"requirements-build.lock"', verifier)
        self.assertIn('"scripts/test/check_environment.py"', verifier)
        self.assertIn('"scripts/test/run_tests.py"', verifier)
        self.assertIn('"diff", "--cached", "--check"', verifier)

    def test_nuitka_includes_customtkinter_package_data(self) -> None:
        with (ROOT / "nuitka.toml").open("rb") as stream:
            options = tomllib.load(stream)["nuitka"]
        self.assertIn("customtkinter", options.get("include_package_data", []))

    def test_required_repository_paths_are_present(self) -> None:
        required = (
            "README.md", "README.txt", "LICENSE", ".gitignore", "requirements.txt", "requirements.lock",
            "CHANGELOG.md", "SECURITY.md", "SUPPORT.md", "CODE_OF_CONDUCT.md", "docs/index.md",
            "docs/release-notes/0.2.1.md", "docs/security/privacy-and-local-data.md",
            ".github/workflows/ci.yml", ".github/workflows/release.yml",
            "scripts/release/verify_release_metadata.py",
            "scripts/release/verify_release_candidate.py",
            "requirements-build.lock", "config/defaults.json", "tests",
        )
        missing = [item for item in required if not (ROOT / item).exists()]
        self.assertEqual(missing, [])

    def test_text_files_contain_no_unexpected_control_characters(self) -> None:
        allowed = {9, 10, 13}
        extensions = {".py", ".md", ".txt", ".toml", ".json", ".yml", ".yaml", ".bat", ".gitignore"}
        failures: list[str] = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.suffix.lower() not in extensions and path.name != ".gitignore":
                continue
            data = path.read_bytes()
            bad = sorted({byte for byte in data if byte < 32 and byte not in allowed})
            if bad:
                failures.append(f"{path.relative_to(ROOT)}: {bad}")
        self.assertEqual(failures, [])

    def test_windows_launchers_reference_existing_python_scripts(self) -> None:
        run_script = (ROOT / "run.bat").read_text(encoding="ascii")
        self.assertIn(r"src\app.py", run_script)
        self.assertTrue((ROOT / "src/app.py").is_file())
        for relative in ("scripts/test/run_tests.bat", "scripts/test/run_pytest.bat"):
            content = (ROOT / relative).read_text(encoding="ascii")
            self.assertIn(r"scripts\test\run_tests.py", content)


if __name__ == "__main__":
    unittest.main()
