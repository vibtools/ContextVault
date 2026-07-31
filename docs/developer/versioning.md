# Versioning

ContextVault uses separate versions for the application and the archive schema.

## Application version

The application follows Semantic Versioning:

```text
MAJOR.MINOR.PATCH
```

Example:

```text
0.2.0
```

- **MAJOR:** breaking product or compatibility change.
- **MINOR:** backward-compatible features or substantial improvements.
- **PATCH:** backward-compatible bug or security fixes.

During the `0.x` development line, releases can still change quickly, but documented compatibility should be preserved whenever practical.

## Git tag

The application version uses a `v` prefix in Git:

```text
v0.2.0
```

## Archive schema version

The archive schema is versioned independently.

Current schema:

```text
1.0
```

Application 0.2.0 can produce archive schema 1.0 because the release fixes implementation behavior without breaking the archive layout.

## Build metadata

The application version must be synchronized in:

```text
src/config/constants.py
pyproject.toml
nuitka.toml
README.md
README.txt
CHANGELOG.md
release notes
vibproject.ygit
generated schemas when they embed application defaults
```

Nuitka fields include project version, `file_version`, and `product_version`.

All must match the release.

## Schema metadata

Schema values remain `1.0` where they describe settings schema, archive schema, or a JSON contract version.

Do not replace every `1.0` string with `0.2.0`.

## Historical correction

The initial public tag line is:

```text
v0.1.0
```

Earlier draft documentation incorrectly displayed application `1.0.0`. That label is corrected in v0.2.0 documentation.

There is no public v1.0.0 release in the documented 0.1.0 to 0.2.0 history.

## Release naming

Recommended title:

```text
ContextVault v0.2.0 — Export Reliability and Stability Update
```

Artifact names remain version-neutral when the workflow uses:

```text
ContextVault-Windows-x64.zip
ContextVault-Windows-x64.zip.sha256
```

The release tag and page identify the version.

## Backward compatibility

A bug-fix release should preserve settings loading, existing archive management, archive schema, public runtime layout, and documented user workflow.

A breaking change requires a new major-version decision, migration guidance, compatibility tests, release notes, and a schema change when archive contracts change.
