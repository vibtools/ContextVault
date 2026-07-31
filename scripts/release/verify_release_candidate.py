"""Create an isolated release environment and run the complete release-candidate verification."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VENV = ROOT / ".venv-release"
REQUIRED_PYTHON = (3, 12)


class VerificationError(RuntimeError):
    """Raised when release verification cannot continue safely."""


def _run(
    command: Sequence[str | os.PathLike[str]],
    *,
    label: str,
    cwd: Path = ROOT,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    printable = " ".join(f'"{item}"' if " " in str(item) else str(item) for item in command)
    print(f"\n==> {label}\n{printable}", flush=True)
    result = subprocess.run(
        [str(item) for item in command],
        cwd=cwd,
        text=True,
        capture_output=capture_output,
        check=False,
    )
    if result.returncode != 0:
        if capture_output:
            if result.stdout:
                print(result.stdout, end="", file=sys.stdout)
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr)
        raise VerificationError(f"{label} failed with exit code {result.returncode}.")
    return result


def _verify_public_repository_boundary(python: Path) -> None:
    _run(
        [python, ROOT / "scripts/release/verify_public_tree.py"],
        label="Verify public repository privacy boundary",
    )


def _python_version(executable: Path) -> tuple[int, int, int] | None:
    result = subprocess.run(
        [
            str(executable),
            "-c",
            "import sys; print('.'.join(map(str, sys.version_info[:3])))",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        major, minor, micro = (int(item) for item in result.stdout.strip().split(".", 2))
    except (TypeError, ValueError):
        return None
    return major, minor, micro


def _resolve_bootstrap_python() -> Path:
    candidates: list[Path] = []

    current = Path(sys.executable).resolve()
    candidates.append(current)

    for name in ("python3.12", "python"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found).resolve())

    if os.name == "nt":
        launcher = shutil.which("py")
        if launcher:
            result = subprocess.run(
                [launcher, "-3.12", "-c", "import sys; print(sys.executable)"],
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                candidates.append(Path(result.stdout.strip()).resolve())

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen or not candidate.is_file():
            continue
        seen.add(candidate)
        version = _python_version(candidate)
        if version and version[:2] == REQUIRED_PYTHON:
            return candidate

    raise VerificationError(
        "Python 3.12 was not found. Install Python 3.12 x64, then run this command again."
    )


def _venv_python(venv_root: Path) -> Path:
    if os.name == "nt":
        return venv_root / "Scripts" / "python.exe"
    return venv_root / "bin" / "python"


def _create_or_repair_environment(
    venv_root: Path,
    *,
    reset: bool,
    include_build_dependencies: bool,
) -> Path:
    if reset and venv_root.exists():
        print(f"Removing existing release environment: {venv_root}")
        shutil.rmtree(venv_root)

    python = _venv_python(venv_root)
    if not python.is_file():
        bootstrap = _resolve_bootstrap_python()
        print(f"Creating isolated Python 3.12 environment with: {bootstrap}")
        subprocess.run(
            [str(bootstrap), "-m", "venv", str(venv_root)],
            cwd=ROOT,
            check=True,
        )
        python = _venv_python(venv_root)

    version = _python_version(python)
    if not version or version[:2] != REQUIRED_PYTHON:
        raise VerificationError(
            f"Release environment must use Python 3.12; found {version!r} at {python}. "
            "Run again with --reset after installing Python 3.12."
        )

    requirements = [ROOT / "requirements.lock"]
    if include_build_dependencies:
        requirements.append(ROOT / "requirements-build.lock")

    install_command: list[str | os.PathLike[str]] = [
        python,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
    ]
    for path in requirements:
        install_command.extend(["--requirement", path])

    _run(
        install_command,
        label="Install exact locked dependencies into .venv-release",
    )
    return python


def _run_worker(args: argparse.Namespace) -> int:
    python = Path(sys.executable).resolve()
    version = sys.version_info[:3]
    if version[:2] != REQUIRED_PYTHON:
        raise VerificationError(
            f"Verification worker requires Python 3.12; found {version[0]}.{version[1]}.{version[2]}."
        )

    print(f"Using isolated interpreter: {python}")
    print(f"Python version: {version[0]}.{version[1]}.{version[2]}")

    _verify_public_repository_boundary(python)

    _run(
        [
            python,
            ROOT / "scripts/release/verify_release_metadata.py",
            "--ref",
            args.ref,
        ],
        label="Verify synchronized release metadata",
    )

    environment_command: list[str | os.PathLike[str]] = [
        python,
        ROOT / "scripts/test/check_environment.py",
    ]
    if args.skip_chrome:
        environment_command.append("--skip-chrome")
    _run(environment_command, label="Verify source and locked runtime environment")

    _run(
        [python, ROOT / "scripts/test/run_tests.py"],
        label="Run complete forensic test suite",
    )

    _run(
        [python, "-m", "compileall", "-q", "src", "scripts", "tests"],
        label="Compile all Python source",
    )

    git = shutil.which("git")
    if git:
        _run([git, "diff", "--check"], label="Check unstaged diff whitespace")
        _run([git, "diff", "--cached", "--check"], label="Check staged diff whitespace")
    else:
        print("NOTICE git was not found; diff whitespace checks were skipped.")

    print("\nRelease-candidate verification passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ref",
        default="main",
        help="Branch or tag name passed to release metadata verification (default: main).",
    )
    parser.add_argument(
        "--skip-chrome",
        action="store_true",
        help="Skip the local Google Chrome presence check. Browser smoke tests remain separate.",
    )
    parser.add_argument(
        "--include-build-dependencies",
        action="store_true",
        help="Also install requirements-build.lock into the isolated environment.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate .venv-release before verification.",
    )
    parser.add_argument(
        "--venv",
        type=Path,
        default=DEFAULT_VENV,
        help="Isolated environment directory (default: .venv-release).",
    )
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.worker:
            return _run_worker(args)

        _verify_public_repository_boundary(Path(sys.executable).resolve())

        venv_root = args.venv
        if not venv_root.is_absolute():
            venv_root = (ROOT / venv_root).resolve()

        python = _create_or_repair_environment(
            venv_root,
            reset=args.reset,
            include_build_dependencies=args.include_build_dependencies,
        )

        worker_command: list[str | os.PathLike[str]] = [
            python,
            Path(__file__).resolve(),
            "--worker",
            "--ref",
            args.ref,
            "--venv",
            venv_root,
        ]
        if args.skip_chrome:
            worker_command.append("--skip-chrome")
        if args.include_build_dependencies:
            worker_command.append("--include-build-dependencies")

        _run(worker_command, label="Run release-candidate verification in isolated environment")
        return 0
    except (OSError, VerificationError, subprocess.SubprocessError) as exc:
        print(f"\nRELEASE VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
