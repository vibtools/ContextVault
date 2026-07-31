"""Forensic source/runtime environment verification for ContextVault."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_PATHS = (
    "src/app.py",
    "requirements.txt",
    "requirements.lock",
    "nuitka.toml",
    "assets/icons/app.ico",
    "config/defaults.json",
    "config/schemas/manifest.schema.json",
    "data/templates/README.txt",
)


def _find_chrome() -> str | None:
    candidates: list[Path] = []
    if platform.system() == "Windows":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            value = __import__("os").environ.get(variable)
            if value:
                candidates.append(Path(value) / "Google/Chrome/Application/chrome.exe")
    else:
        for name in ("google-chrome", "google-chrome-stable", "chrome"):
            found = shutil.which(name)
            if found:
                return found
    return next((str(path) for path in candidates if path.is_file()), None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-chrome", action="store_true", help="Do not require Google Chrome.")
    parser.add_argument("--skip-modules", action="store_true", help="Do not verify installed Python modules.")
    args = parser.parse_args()
    failures: list[str] = []

    if sys.version_info < (3, 12):
        failures.append(f"Python 3.12+ required; found {platform.python_version()}")
    else:
        print(f"PASS Python {platform.python_version()} ({sys.executable})")

    for relative in REQUIRED_PATHS:
        path = ROOT / relative
        if path.exists():
            print(f"PASS {relative}")
        else:
            failures.append(f"Missing required path: {relative}")

    try:
        with (ROOT / "nuitka.toml").open("rb") as stream:
            tomllib.load(stream)
        json.loads((ROOT / "config/defaults.json").read_text(encoding="utf-8"))
        json.loads((ROOT / "vibproject.ygit").read_text(encoding="utf-8"))
        print("PASS TOML and JSON configuration parse")
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        failures.append(f"Configuration parse failed: {exc}")

    if not args.skip_modules:
        result = subprocess.run([sys.executable, str(ROOT / "scripts/test/checkmodules.py")], cwd=ROOT)
        if result.returncode != 0:
            failures.append("Locked module verification failed for the active Python interpreter.")

    if not args.skip_chrome:
        chrome = _find_chrome()
        if chrome:
            print(f"PASS Google Chrome: {chrome}")
        else:
            failures.append("Google Chrome Stable was not found.")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 1
    print("Environment verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
