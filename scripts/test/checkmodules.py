"""Verify required ContextVault Python modules and locked versions."""

from __future__ import annotations

import importlib
import importlib.metadata
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Requirement:
    distribution: str
    module: str
    version: str


REQUIREMENTS = (
    Requirement("customtkinter", "customtkinter", "5.2.2"),
    Requirement("playwright", "playwright", "1.60.0"),
    Requirement("beautifulsoup4", "bs4", "4.13.5"),
    Requirement("markdownify", "markdownify", "1.2.0"),
    Requirement("Pillow", "PIL", "11.3.0"),
    Requirement("pydantic", "pydantic", "2.11.7"),
    Requirement("tenacity", "tenacity", "9.1.2"),
)


def main() -> int:
    failures: list[str] = []
    for requirement in REQUIREMENTS:
        try:
            importlib.import_module(requirement.module)
            installed = importlib.metadata.version(requirement.distribution)
        except (ImportError, importlib.metadata.PackageNotFoundError) as exc:
            failures.append(f"{requirement.distribution}: unavailable ({exc})")
            continue
        if installed != requirement.version:
            failures.append(
                f"{requirement.distribution}: expected {requirement.version}, installed {installed}"
            )
        else:
            print(f"PASS {requirement.distribution}=={installed}")
    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        print(f"Active interpreter: {sys.executable}", file=sys.stderr)
        print(
            "The project lock is correct; the active Python environment is out of sync. "
            "Run: python scripts/release/verify_release_candidate.py --ref main --skip-chrome",
            file=sys.stderr,
        )
        return 1
    print("All locked runtime modules are available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
