"""Verify that release identity is synchronized before build or publication."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VERSIONED_SCHEMA_FILES = (
    "chunk-map.schema.json",
    "conversation.schema.json",
    "manifest.schema.json",
    "metadata.schema.json",
    "rag-chunks.schema.json",
    "rag-documents.schema.json",
    "rag-keywords.schema.json",
    "search-index.schema.json",
    "statistics.schema.json",
    "summary.schema.json",
)
VERSION_PROPERTY_NAMES = {"version", "contextvaultVersion", "exportEngineVersion"}


def _application_version() -> str:
    path = ROOT / "src/config/constants.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "APPLICATION_VERSION" for target in node.targets):
            continue
        value = ast.literal_eval(node.value)
        if isinstance(value, str) and re.fullmatch(r"\d+\.\d+\.\d+", value):
            return value
    raise ValueError("APPLICATION_VERSION must be a literal semantic version.")


def _load_toml(relative: str) -> dict[str, Any]:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


def _load_json(relative: str) -> dict[str, Any]:
    payload = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{relative} must contain a JSON object.")
    return payload


def _schema_version_defaults(payload: Any) -> list[str]:
    defaults: list[str] = []
    if isinstance(payload, dict):
        properties = payload.get("properties")
        if isinstance(properties, dict):
            for name, schema in properties.items():
                if name in VERSION_PROPERTY_NAMES and isinstance(schema, dict):
                    default = schema.get("default")
                    if isinstance(default, str):
                        defaults.append(default)
        for value in payload.values():
            defaults.extend(_schema_version_defaults(value))
    elif isinstance(payload, list):
        for value in payload:
            defaults.extend(_schema_version_defaults(value))
    return defaults


def verify_release_metadata(ref_name: str = "") -> list[str]:
    """Return every release metadata inconsistency without mutating the repository."""
    errors: list[str] = []
    try:
        version = _application_version()
    except (OSError, SyntaxError, ValueError) as exc:
        return [f"Unable to read application version: {exc}"]

    expected_tag = f"v{version}"
    try:
        pyproject = _load_toml("pyproject.toml")
        nuitka = _load_toml("nuitka.toml")
        manifest = _load_json("vibproject.ygit")
    except (OSError, ValueError, KeyError, tomllib.TOMLDecodeError, json.JSONDecodeError) as exc:
        return [f"Unable to parse release metadata: {exc}"]

    checks = {
        "pyproject.toml project.version": pyproject.get("project", {}).get("version"),
        "nuitka.toml project.version": nuitka.get("project", {}).get("version"),
        "nuitka.toml nuitka.file_version": nuitka.get("nuitka", {}).get("file_version"),
        "nuitka.toml nuitka.product_version": nuitka.get("nuitka", {}).get("product_version"),
        "vibproject.ygit project.version": manifest.get("project", {}).get("version"),
        "vibproject.ygit release.latestVersion": manifest.get("release", {}).get("latestVersion"),
    }
    for label, actual in checks.items():
        if actual != version:
            errors.append(f"{label} is {actual!r}; expected {version!r}.")

    project_status = manifest.get("project", {}).get("status")
    if project_status != "stable":
        errors.append(f"vibproject.ygit project.status is {project_status!r}; expected 'stable'.")

    private_path = manifest.get("paths", {}).get("project")
    if private_path == "project/":
        errors.append("vibproject.ygit still points to the private project/ directory.")

    for name in VERSIONED_SCHEMA_FILES:
        relative = f"config/schemas/{name}"
        try:
            defaults = _schema_version_defaults(_load_json(relative))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"Unable to validate {relative}: {exc}")
            continue
        if not defaults:
            errors.append(f"{relative} contains no application-version default.")
        for default in defaults:
            if default != version:
                errors.append(f"{relative} contains application-version default {default!r}; expected {version!r}.")

    required_text = {
        "README.md": f"Application version:** {version}",
        "README.txt": f"ContextVault {version}",
        "CHANGELOG.md": f"## [{version}]",
        f"docs/release-notes/{version}.md": f"# ContextVault {expected_tag}",
        "data/templates/README.txt": f"Application release: {version}",
        "requirements.txt": f"ContextVault v{version}",
        "requirements.lock": f"ContextVault v{version}",
        "requirements-build.lock": f"ContextVault v{version}",
    }
    for relative, marker in required_text.items():
        path = ROOT / relative
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"Unable to read {relative}: {exc}")
            continue
        if marker not in content:
            errors.append(f"{relative} does not contain required release marker {marker!r}.")

    verifier = ROOT / "scripts/release/verify_release_candidate.py"
    if not verifier.is_file():
        errors.append("scripts/release/verify_release_candidate.py is missing.")

    normalized_ref = ref_name.strip()
    if normalized_ref.startswith("refs/tags/"):
        normalized_ref = normalized_ref.removeprefix("refs/tags/")
    if normalized_ref.startswith("v") and normalized_ref != expected_tag:
        errors.append(f"Workflow tag {normalized_ref!r} does not match application tag {expected_tag!r}.")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ref",
        default="",
        help="Current branch or tag name. Tag refs must match v<APPLICATION_VERSION>.",
    )
    args = parser.parse_args()
    errors = verify_release_metadata(args.ref)
    if errors:
        print("Release metadata verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    version = _application_version()
    ref_label = args.ref.strip() or "local source"
    print(f"Release metadata verification passed for ContextVault {version} ({ref_label}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
