"""Build the official ContextVault Windows x64 Nuitka OneDir distribution.

This module is the single translation boundary between ``nuitka.toml`` and the
Nuitka command line used by local release builds and GitHub Actions.
"""

from __future__ import annotations

import importlib.metadata
import os
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "nuitka.toml"
BUILD_LOCK_PATH = ROOT / "requirements-build.lock"
DISTRIBUTION_MARKER = "distribution-path.txt"
COMMAND_RECORD = "nuitka-command.txt"

REQUIRED_DISTRIBUTION_PATHS = (
    "ContextVault.exe",
    "README.txt",
    "LICENSE",
    "data",
    "exports",
    "logs",
    "runtime",
    "runtime/assets",
    "runtime/config",
    "runtime/config/defaults.json",
    "runtime/icons",
    "runtime/schemas",
    "runtime/templates",
    "runtime/themes",
)

_ALLOWED_PROJECT_KEYS = {"name", "version", "main_file"}
_ALLOWED_NUITKA_KEYS = {
    "standalone",
    "onefile",
    "output_dir",
    "output_filename",
    "follow_imports",
    "lto",
    "windows_console_mode",
    "remove_output",
    "report",
    "company_name",
    "product_name",
    "file_version",
    "product_version",
    "copyright",
    "windows_icon_from_ico",
    "enable_plugin",
    "include_package_data",
    "include_package",
    "include_data_dir",
    "include_data_files",
    "nofollow_import_to",
    "noinclude_default_mode",
    "assume_yes_for_downloads",
    "low_memory",
    "jobs",
    "msvc",
}
_VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")


class BuildConfigurationError(ValueError):
    """Raised when the checked-in release build configuration is invalid."""


@dataclass(frozen=True)
class BuildConfiguration:
    """Validated official build configuration."""

    project_name: str
    project_version: str
    main_file: str
    standalone: bool
    onefile: bool
    output_dir: str
    output_filename: str
    follow_imports: bool
    lto: str
    windows_console_mode: str
    remove_output: bool
    report: str
    company_name: str
    product_name: str
    file_version: str
    product_version: str
    copyright: str
    windows_icon_from_ico: str
    enable_plugin: tuple[str, ...]
    include_package_data: tuple[str, ...]
    include_package: tuple[str, ...]
    include_data_dir: tuple[str, ...]
    include_data_files: tuple[str, ...]
    nofollow_import_to: tuple[str, ...]
    noinclude_default_mode: str
    assume_yes_for_downloads: bool
    low_memory: bool
    jobs: int
    msvc: str


def _require_mapping(payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise BuildConfigurationError(f"{label} must be a TOML table.")
    return payload


def _require_string(payload: dict[str, Any], key: str, table: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BuildConfigurationError(f"{table}.{key} must be a non-empty string.")
    return value.strip()


def _require_bool(payload: dict[str, Any], key: str, table: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise BuildConfigurationError(f"{table}.{key} must be true or false.")
    return value


def _require_int(payload: dict[str, Any], key: str, table: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise BuildConfigurationError(f"{table}.{key} must be an integer.")
    return value


def _require_string_tuple(payload: dict[str, Any], key: str, table: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise BuildConfigurationError(f"{table}.{key} must be an array of non-empty strings.")
    return tuple(item.strip() for item in value)


def _validate_known_keys(payload: dict[str, Any], allowed: set[str], table: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise BuildConfigurationError(f"Unsupported {table} key(s): {unknown}")


def _resolve_repository_path(root: Path, relative: str, label: str, *, must_exist: bool = True) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise BuildConfigurationError(f"{label} must be repository-relative: {relative!r}")
    root_resolved = root.resolve()
    resolved = (root_resolved / candidate).resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise BuildConfigurationError(f"{label} escapes the repository: {relative!r}")
    if must_exist and not resolved.exists():
        raise BuildConfigurationError(f"{label} does not exist: {relative!r}")
    return resolved


def _validate_distribution_target(target: str, label: str) -> str:
    normalized = target.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise BuildConfigurationError(f"{label} must be a safe relative distribution path: {target!r}")
    return path.as_posix()


def _parse_mapping(root: Path, value: str, label: str) -> tuple[Path, str]:
    if "=" not in value:
        raise BuildConfigurationError(f"{label} must use SOURCE=DESTINATION syntax: {value!r}")
    source, target = value.split("=", 1)
    source_path = _resolve_repository_path(root, source.strip(), f"{label} source")
    target_path = _validate_distribution_target(target, f"{label} destination")
    return source_path, target_path


def load_configuration(root: Path = ROOT, config_path: Path | None = None) -> BuildConfiguration:
    """Load and validate the checked-in ``nuitka.toml`` configuration."""

    root = root.resolve()
    path = (config_path or root / "nuitka.toml").resolve()
    if path != root / "nuitka.toml":
        if root not in path.parents:
            raise BuildConfigurationError("The build configuration must be inside the repository.")
    try:
        with path.open("rb") as stream:
            payload = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise BuildConfigurationError(f"Unable to read {path}: {exc}") from exc

    project = _require_mapping(payload.get("project"), "project")
    nuitka = _require_mapping(payload.get("nuitka"), "nuitka")
    _validate_known_keys(project, _ALLOWED_PROJECT_KEYS, "project")
    _validate_known_keys(nuitka, _ALLOWED_NUITKA_KEYS, "nuitka")

    configuration = BuildConfiguration(
        project_name=_require_string(project, "name", "project"),
        project_version=_require_string(project, "version", "project"),
        main_file=_require_string(project, "main_file", "project"),
        standalone=_require_bool(nuitka, "standalone", "nuitka"),
        onefile=_require_bool(nuitka, "onefile", "nuitka"),
        output_dir=_require_string(nuitka, "output_dir", "nuitka"),
        output_filename=_require_string(nuitka, "output_filename", "nuitka"),
        follow_imports=_require_bool(nuitka, "follow_imports", "nuitka"),
        lto=_require_string(nuitka, "lto", "nuitka"),
        windows_console_mode=_require_string(nuitka, "windows_console_mode", "nuitka"),
        remove_output=_require_bool(nuitka, "remove_output", "nuitka"),
        report=_require_string(nuitka, "report", "nuitka"),
        company_name=_require_string(nuitka, "company_name", "nuitka"),
        product_name=_require_string(nuitka, "product_name", "nuitka"),
        file_version=_require_string(nuitka, "file_version", "nuitka"),
        product_version=_require_string(nuitka, "product_version", "nuitka"),
        copyright=_require_string(nuitka, "copyright", "nuitka"),
        windows_icon_from_ico=_require_string(nuitka, "windows_icon_from_ico", "nuitka"),
        enable_plugin=_require_string_tuple(nuitka, "enable_plugin", "nuitka"),
        include_package_data=_require_string_tuple(nuitka, "include_package_data", "nuitka"),
        include_package=_require_string_tuple(nuitka, "include_package", "nuitka"),
        include_data_dir=_require_string_tuple(nuitka, "include_data_dir", "nuitka"),
        include_data_files=_require_string_tuple(nuitka, "include_data_files", "nuitka"),
        nofollow_import_to=_require_string_tuple(nuitka, "nofollow_import_to", "nuitka"),
        noinclude_default_mode=_require_string(nuitka, "noinclude_default_mode", "nuitka"),
        assume_yes_for_downloads=_require_bool(nuitka, "assume_yes_for_downloads", "nuitka"),
        low_memory=_require_bool(nuitka, "low_memory", "nuitka"),
        jobs=_require_int(nuitka, "jobs", "nuitka"),
        msvc=_require_string(nuitka, "msvc", "nuitka"),
    )

    if configuration.project_name != "ContextVault":
        raise BuildConfigurationError("project.name must be 'ContextVault'.")
    if not _VERSION_PATTERN.fullmatch(configuration.project_version):
        raise BuildConfigurationError("project.version must be a three-part semantic version.")
    if configuration.file_version != configuration.project_version:
        raise BuildConfigurationError("nuitka.file_version must match project.version.")
    if configuration.product_version != configuration.project_version:
        raise BuildConfigurationError("nuitka.product_version must match project.version.")
    if not configuration.standalone or configuration.onefile:
        raise BuildConfigurationError("The official release must be standalone OneDir, not onefile.")
    if configuration.output_filename != "ContextVault":
        raise BuildConfigurationError("nuitka.output_filename must be 'ContextVault'.")
    if configuration.lto != "no":
        raise BuildConfigurationError(
            "nuitka.lto must be 'no' for the official memory-safe Windows release build."
        )
    if not configuration.low_memory:
        raise BuildConfigurationError(
            "nuitka.low_memory must be true for the official Windows release build."
        )
    if configuration.jobs != 1:
        raise BuildConfigurationError(
            "nuitka.jobs must be 1 for deterministic low-memory Windows compilation."
        )

    _resolve_repository_path(root, configuration.main_file, "project.main_file")
    _resolve_repository_path(root, configuration.windows_icon_from_ico, "nuitka.windows_icon_from_ico")
    _resolve_repository_path(root, configuration.output_dir, "nuitka.output_dir", must_exist=False)
    _resolve_repository_path(root, configuration.report, "nuitka.report", must_exist=False)

    for index, value in enumerate(configuration.include_data_dir):
        source, _ = _parse_mapping(root, value, f"nuitka.include_data_dir[{index}]")
        if not source.is_dir():
            raise BuildConfigurationError(f"nuitka.include_data_dir[{index}] source is not a directory: {source}")
    for index, value in enumerate(configuration.include_data_files):
        source, _ = _parse_mapping(root, value, f"nuitka.include_data_files[{index}]")
        if not source.is_file():
            raise BuildConfigurationError(f"nuitka.include_data_files[{index}] source is not a file: {source}")

    return configuration


def _append_repeated(command: list[str], option: str, values: Iterable[str]) -> None:
    for value in values:
        command.append(f"{option}={value}")


def build_command(
    configuration: BuildConfiguration,
    root: Path = ROOT,
    python_executable: str | Path | None = None,
) -> list[str]:
    """Translate the validated TOML configuration into a deterministic command."""

    root = root.resolve()
    executable = str(Path(python_executable or sys.executable).resolve())
    output_dir = _resolve_repository_path(root, configuration.output_dir, "nuitka.output_dir", must_exist=False)
    report = _resolve_repository_path(root, configuration.report, "nuitka.report", must_exist=False)
    icon = _resolve_repository_path(root, configuration.windows_icon_from_ico, "nuitka.windows_icon_from_ico")
    main_file = _resolve_repository_path(root, configuration.main_file, "project.main_file")

    command = [
        executable,
        "-m",
        "nuitka",
        "--mode=standalone",
        f"--output-dir={output_dir}",
        f"--output-filename={configuration.output_filename}",
        f"--lto={configuration.lto}",
        f"--jobs={configuration.jobs}",
        f"--windows-console-mode={configuration.windows_console_mode}",
        f"--report={report}",
        f"--company-name={configuration.company_name}",
        f"--product-name={configuration.product_name}",
        f"--file-version={configuration.file_version}",
        f"--product-version={configuration.product_version}",
        f"--copyright={configuration.copyright}",
        f"--windows-icon-from-ico={icon}",
        f"--noinclude-default-mode={configuration.noinclude_default_mode}",
        f"--msvc={configuration.msvc}",
    ]
    if configuration.follow_imports:
        command.append("--follow-imports")
    if configuration.remove_output:
        command.append("--remove-output")
    if configuration.assume_yes_for_downloads:
        command.append("--assume-yes-for-downloads")
    if configuration.low_memory:
        command.append("--low-memory")

    _append_repeated(command, "--enable-plugin", configuration.enable_plugin)
    _append_repeated(command, "--include-package-data", configuration.include_package_data)
    _append_repeated(command, "--include-package", configuration.include_package)
    for index, value in enumerate(configuration.include_data_dir):
        source, target = _parse_mapping(root, value, f"nuitka.include_data_dir[{index}]")
        command.append(f"--include-data-dir={source}={target}")
    for index, value in enumerate(configuration.include_data_files):
        source, target = _parse_mapping(root, value, f"nuitka.include_data_files[{index}]")
        command.append(f"--include-data-files={source}={target}")
    _append_repeated(command, "--nofollow-import-to", configuration.nofollow_import_to)
    command.append(str(main_file))
    return command


def _locked_nuitka_version(lock_path: Path) -> str:
    try:
        lines = lock_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise BuildConfigurationError(f"Unable to read {lock_path}: {exc}") from exc
    matches = [line.strip().split("==", 1)[1] for line in lines if line.strip().lower().startswith("nuitka==")]
    if len(matches) != 1 or not matches[0]:
        raise BuildConfigurationError("requirements-build.lock must contain exactly one Nuitka==<version> entry.")
    return matches[0]


def verify_build_runtime(root: Path = ROOT) -> None:
    """Verify the interpreter and locked Nuitka build dependency."""

    if os.name != "nt":
        raise RuntimeError("The official ContextVault release build is supported only on Windows.")
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError(f"Python 3.12 is required; running {sys.version.split()[0]}.")
    expected = _locked_nuitka_version(root / "requirements-build.lock")
    try:
        installed = importlib.metadata.version("Nuitka")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("Nuitka is not installed in the active release environment.") from exc
    if installed != expected:
        raise RuntimeError(f"Nuitka version mismatch: expected {expected}, installed {installed}.")


def prepare_output_directory(configuration: BuildConfiguration, root: Path = ROOT) -> Path:
    """Remove stale build output and create a deterministic empty build root."""

    output_dir = _resolve_repository_path(root.resolve(), configuration.output_dir, "nuitka.output_dir", must_exist=False)
    if output_dir == root.resolve():
        raise BuildConfigurationError("The build output directory cannot be the repository root.")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def locate_distribution(configuration: BuildConfiguration, root: Path = ROOT) -> Path:
    """Locate exactly one successful Nuitka OneDir distribution."""

    output_dir = _resolve_repository_path(root.resolve(), configuration.output_dir, "nuitka.output_dir")
    executable_name = f"{configuration.output_filename}.exe"
    candidates = sorted(
        path.resolve()
        for path in output_dir.glob("*.dist")
        if path.is_dir() and (path / executable_name).is_file()
    )
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected exactly one .dist directory containing {executable_name}; found {candidates}."
        )
    return candidates[0]


def finalize_distribution(configuration: BuildConfiguration, root: Path = ROOT) -> Path:
    """Create writable portable directories, validate contents, and write marker."""

    output_dir = _resolve_repository_path(root.resolve(), configuration.output_dir, "nuitka.output_dir")
    distribution = locate_distribution(configuration, root)
    for relative in ("data", "exports", "logs"):
        (distribution / relative).mkdir(parents=True, exist_ok=True)

    missing = [relative for relative in REQUIRED_DISTRIBUTION_PATHS if not (distribution / relative).exists()]
    if missing:
        raise RuntimeError(f"Nuitka distribution is missing required release paths: {missing}")
    executable = distribution / f"{configuration.output_filename}.exe"
    if executable.stat().st_size <= 0:
        raise RuntimeError(f"Compiled executable is empty: {executable}")

    marker = output_dir / DISTRIBUTION_MARKER
    marker.write_text(f"{distribution}\n", encoding="utf-8", newline="\n")
    return distribution


def run_build(root: Path = ROOT) -> Path:
    """Run the official deterministic Windows build and return the .dist path."""

    root = root.resolve()
    configuration = load_configuration(root)
    verify_build_runtime(root)
    output_dir = prepare_output_directory(configuration, root)
    command = build_command(configuration, root)
    (output_dir / COMMAND_RECORD).write_text(
        subprocess.list2cmdline(command) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    subprocess.run(command, cwd=root, check=True)
    return finalize_distribution(configuration, root)


def main() -> int:
    try:
        distribution = run_build(ROOT)
    except (BuildConfigurationError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ContextVault Windows build failed: {exc}", file=sys.stderr)
        return 1
    print(f"ContextVault Windows distribution: {distribution}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
