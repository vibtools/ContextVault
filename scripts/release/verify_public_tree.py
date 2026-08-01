"""Verify that private and runtime-only paths cannot enter the public Git tree."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_IGNORE_RULES = (
    "__pycache__/",
    "*.py[cod]",
    "/project/",
    ".venv-release/",
    "data/chrome-user-data/",
    "data/settings.json",
    "data/export_history.json",
    "data/checkpoints/",
    "exports/",
    "logs/",
    "/build/",
    "/dist/",
    "/artifacts/",
)

EXCLUDED_PREFIXES = (
    "project/",
    ".venv-release/",
    "data/chrome-user-data/",
    "data/checkpoints/",
    "exports/",
    "logs/",
    "build/",
    "dist/",
    "artifacts/",
)

EXCLUDED_EXACT_PATHS = {
    "data/settings.json",
    "data/export_history.json",
}

REQUIRED_TRACKABLE_PATHS = (
    "scripts/build/build_windows.py",
)

REQUIRED_IGNORED_PROBES = (
    "project/",
    ".venv-release/",
    "build/generated.bin",
    "dist/generated.bin",
    "artifacts/generated.bin",
    "scripts/build/__pycache__/build_windows.pyc",
)


class PublicTreeVerificationError(RuntimeError):
    """Raised when the public repository boundary cannot be verified."""


def _normalized_path(value: str) -> str:
    return value.replace("\\", "/").removeprefix("./")


def _is_excluded_path(value: str) -> bool:
    path = _normalized_path(value)
    if path in EXCLUDED_EXACT_PATHS:
        return True
    if any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return True

    parts = path.split("/")
    if any(part in {"__pycache__", ".pytest_cache"} for part in parts):
        return True
    if path.endswith((".pyc", ".pyo", ".log", ".partial", ".invalid")):
        return True
    if ".partial-" in path or ".invalid-" in path:
        return True
    if Path(path).name.startswith(".cv-") and path.endswith(".tmp"):
        return True
    if path.endswith(".zip") and not path.startswith("tests/fixtures/"):
        return True
    return False


def _run_git(
    git: str,
    root: Path,
    arguments: Sequence[str],
    *,
    accepted_return_codes: set[int] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    accepted = accepted_return_codes or {0}
    result = subprocess.run(
        [git, "-C", str(root), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode not in accepted:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise PublicTreeVerificationError(
            f"git {' '.join(arguments)} failed with exit code {result.returncode}: {stderr}"
        )
    return result


def _split_nul(payload: bytes) -> list[str]:
    return [
        item.decode("utf-8", errors="surrogateescape")
        for item in payload.split(b"\0")
        if item
    ]


def verify_public_tree(root: Path = ROOT) -> list[str]:
    """Return all public-tree boundary violations for *root*."""

    errors: list[str] = []
    root = root.resolve()
    git = shutil.which("git")
    if not git:
        return ["Git is required for release verification but was not found on PATH."]

    try:
        top_level_result = _run_git(git, root, ["rev-parse", "--show-toplevel"])
        top_level_text = top_level_result.stdout.decode("utf-8", errors="replace").strip()
        top_level = Path(top_level_text).resolve()
        if os.path.normcase(str(top_level)) != os.path.normcase(str(root)):
            errors.append(
                f"Verification root {root} is not the Git repository root {top_level}."
            )
    except (OSError, PublicTreeVerificationError, ValueError) as exc:
        return [f"Unable to resolve the Git repository root: {exc}"]

    gitignore = root / ".gitignore"
    try:
        ignore_lines = {
            line.strip()
            for line in gitignore.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
    except OSError as exc:
        errors.append(f"Unable to read .gitignore: {exc}")
        ignore_lines = set()

    for rule in REQUIRED_IGNORE_RULES:
        if rule not in ignore_lines:
            errors.append(f".gitignore is missing mandatory public-boundary rule {rule!r}.")

    for relative in REQUIRED_TRACKABLE_PATHS:
        source = root / relative
        if not source.is_file():
            errors.append(f"Required public release source is missing: {relative}")
            continue
        try:
            result = _run_git(
                git,
                root,
                ["check-ignore", "--quiet", "--no-index", relative],
                accepted_return_codes={0, 1},
            )
            if result.returncode == 0:
                errors.append(f"Required public release source is ignored: {relative}")
        except (OSError, PublicTreeVerificationError) as exc:
            errors.append(f"Unable to verify trackability for {relative!r}: {exc}")

    for probe in REQUIRED_IGNORED_PROBES:
        try:
            result = _run_git(
                git,
                root,
                ["check-ignore", "--quiet", "--no-index", probe],
                accepted_return_codes={0, 1},
            )
            if result.returncode != 0:
                errors.append(f"Git does not treat {probe!r} as ignored.")
        except (OSError, PublicTreeVerificationError) as exc:
            errors.append(f"Unable to verify ignore behavior for {probe!r}: {exc}")

    try:
        tracked_result = _run_git(git, root, ["ls-files", "-z"])
        tracked_paths = _split_nul(tracked_result.stdout)
        excluded_tracked = sorted(path for path in tracked_paths if _is_excluded_path(path))
        if excluded_tracked:
            errors.append(
                "The Git index contains private/runtime-only paths: "
                + ", ".join(excluded_tracked)
            )
    except (OSError, PublicTreeVerificationError) as exc:
        errors.append(f"Unable to inspect the Git index: {exc}")

    try:
        staged_result = _run_git(
            git,
            root,
            ["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        )
        staged_paths = _split_nul(staged_result.stdout)
        excluded_staged = sorted(path for path in staged_paths if _is_excluded_path(path))
        if excluded_staged:
            errors.append(
                "The staged release contains private/runtime-only additions or modifications: "
                + ", ".join(excluded_staged)
            )
    except (OSError, PublicTreeVerificationError) as exc:
        errors.append(f"Unable to inspect staged paths: {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root to verify (default: current ContextVault repository).",
    )
    args = parser.parse_args()

    errors = verify_public_tree(args.root)
    if errors:
        print("Public repository boundary verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("PASS Git repository root is valid.")
    print("PASS required public release-build sources are present and trackable.")
    print("PASS private, runtime, cache, and generated-output paths are ignored.")
    print("PASS no private or runtime-only paths are present in the Git index.")
    print("PASS no private or runtime-only additions are staged.")
    print("Public repository boundary verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
