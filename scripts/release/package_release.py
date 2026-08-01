"""Create the frozen Windows ZIP release and SHA-256 checksum."""

from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_ROOT = ROOT / "build"
ARTIFACT_DIR = ROOT / "artifacts"
ARCHIVE_NAME = "ContextVault-Windows-x64.zip"

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


def _resolve_build_directory() -> Path:
    marker = BUILD_ROOT / "distribution-path.txt"
    if marker.is_file():
        candidate = Path(marker.read_text(encoding="utf-8").strip()).resolve()
        if candidate.parent == BUILD_ROOT.resolve() and candidate.name.endswith(".dist"):
            return candidate
    candidates = sorted(path for path in BUILD_ROOT.glob("*.dist") if (path / "ContextVault.exe").is_file())
    if len(candidates) != 1:
        raise FileNotFoundError(f"Expected one ContextVault .dist folder, found: {candidates}")
    return candidates[0]


def main() -> int:
    try:
        build_dir = _resolve_build_directory()
    except (OSError, ValueError) as exc:
        print(f"Unable to resolve release distribution: {exc}", file=sys.stderr)
        return 1
    missing = [relative for relative in REQUIRED_DISTRIBUTION_PATHS if not (build_dir / relative).exists()]
    if missing:
        print(f"Missing release distribution paths: {missing}", file=sys.stderr)
        return 1
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = ARTIFACT_DIR / ARCHIVE_NAME
    temporary = archive_path.with_suffix(".zip.partial")
    temporary.unlink(missing_ok=True)
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(build_dir.rglob("*")):
            relative = (Path("ContextVault") / path.relative_to(build_dir)).as_posix()
            if path.is_dir():
                archive.writestr(relative.rstrip("/") + "/", b"")
            elif path.is_file():
                archive.write(path, arcname=relative)
    temporary.replace(archive_path)
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    checksum_path = ARTIFACT_DIR / f"{ARCHIVE_NAME}.sha256"
    checksum_path.write_text(f"{checksum}  {ARCHIVE_NAME}\n", encoding="utf-8", newline="\n")
    with zipfile.ZipFile(archive_path) as archive:
        bad_file = archive.testzip()
        if bad_file is not None:
            print(f"Corrupt ZIP member: {bad_file}", file=sys.stderr)
            return 1
        names = set(archive.namelist())
        required_members = {
            "ContextVault/ContextVault.exe",
            "ContextVault/README.txt",
            "ContextVault/LICENSE",
            "ContextVault/data/",
            "ContextVault/exports/",
            "ContextVault/logs/",
            "ContextVault/runtime/",
            "ContextVault/runtime/assets/",
            "ContextVault/runtime/config/",
            "ContextVault/runtime/config/defaults.json",
            "ContextVault/runtime/icons/",
            "ContextVault/runtime/schemas/",
            "ContextVault/runtime/templates/",
            "ContextVault/runtime/themes/",
        }
        missing_members = sorted(required_members - names)
        if missing_members:
            print(f"ZIP is missing required members: {missing_members}", file=sys.stderr)
            return 1
    print(archive_path)
    print(checksum_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
