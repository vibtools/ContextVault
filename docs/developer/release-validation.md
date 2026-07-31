# Release Validation — ContextVault v0.2.0

This document defines the required evidence for publishing v0.2.0.

It intentionally distinguishes source CI from the final Windows executable build.

## Release identity

```text
Application version: 0.2.0
Git tag: v0.2.0
Archive schema: 1.0
Release asset: ContextVault-Windows-x64.zip
Checksum: ContextVault-Windows-x64.zip.sha256
```

## Gate 1: Source integrity

Required:

- clean Git working tree;
- no merge conflicts;
- no runtime profile, settings, checkpoints, exports, or logs tracked;
- public documentation contains no dependency on unavailable private files;
- application version metadata synchronized;
- archive schema unchanged unless explicitly approved.

Commands:

```powershell
git status
git diff --check
git ls-files -- data/chrome-user-data data/checkpoints exports logs project
git grep -n -E "project[\\/]" -- "*.md" "*.txt"
git grep -n "1\.0\.0" -- "*.md" "*.txt" "pyproject.toml" "nuitka.toml" "vibproject.ygit"
```

Interpret version matches carefully: archive schema `1.0` is valid; application release `1.0.0` is not the v0.2.0 identity.

## Gate 2: Documentation

Required public documents:

- README and portable README;
- changelog;
- installation, quick start, usage, and settings;
- upgrade and checksum verification;
- troubleshooting and FAQ;
- privacy, limitations, support, and security;
- v0.2.0 release notes;
- architecture, traceability, validation, and release process.

Required checks:

- all relative links resolve;
- no broken private-folder references;
- no false claim that Nuitka passed before the build runs;
- no claim that a live authenticated export passed without evidence;
- user instructions match current UI labels and defaults.

## Gate 3: Local source verification

Use the isolated release verifier so packages installed in a shared Python environment cannot change the result:

```powershell
python scripts/release/verify_release_candidate.py --ref main --skip-chrome
```

To recreate the environment and install build tooling too:

```powershell
python scripts/release/verify_release_candidate.py `
    --ref main `
    --skip-chrome `
    --reset `
    --include-build-dependencies
```

Expected:

- `.venv-release` is created or repaired with Python 3.12;
- exact packages from `requirements.lock` are installed;
- release metadata verification passes;
- environment checks pass;
- all 81 tests pass;
- compileall returns zero;
- staged and unstaged whitespace checks return zero.

Diagnostic lines from intentionally invalid test fixtures are acceptable only when their test ends with `ok` and the suite ends with `OK`.

## Gate 4: Windows source CI

The `CI` workflow must pass for the final release-preparation commit.

It verifies Python 3.12 setup, locked runtime dependencies, source environment, and the forensic test suite.

Evidence for the earlier bug-fix commit:

```text
Run ID: 30652247576
Job: Windows Python 3.12
Result: success
Tests: 81 passed
```

A later documentation and version commit requires its own successful CI run.

## Gate 5: Operational browser smoke test

Before tagging:

1. start the final source or local release candidate;
2. Launch Chrome with managed profile;
3. confirm manual ChatGPT login;
4. scan conversations;
5. export a small text conversation;
6. export an image-containing conversation;
7. export a long conversation;
8. confirm canonical title;
9. confirm no duplicate export interleaving;
10. cancel one export and confirm cancellation logs;
11. validate resulting archives.

Do not claim this gate passed without a complete real run.

## Gate 6: Version synchronization

Before tagging, verify:

```text
src/config/constants.py
pyproject.toml
nuitka.toml
README.md
README.txt
CHANGELOG.md
docs/release-notes/0.2.0.md
vibproject.ygit
generated schema defaults where application version is embedded
```

Application release values must be `0.2.0`.

Archive schema values remain `1.0`.

## Gate 7: Tag-triggered Build and Release workflow

Push annotated tag:

```powershell
git tag -a v0.2.0 -m "ContextVault v0.2.0 - Export reliability and stability"
git push origin v0.2.0
```

The workflow must pass checkout, Python setup, dependency install, environment verification, tests, MSVC/Nuitka compile, package verification, artifact upload, GitHub Release creation, and release asset upload.

## Gate 8: Release asset verification

Download the published assets and verify:

```powershell
$expected = ((Get-Content ".\ContextVault-Windows-x64.zip.sha256" -Raw).Trim() -split "\s+")[0].ToLower()
$actual = (Get-FileHash ".\ContextVault-Windows-x64.zip" -Algorithm SHA256).Hash.ToLower()
if ($actual -ne $expected) { throw "Checksum mismatch" }
```

Extract and confirm required paths.

## Gate 9: Portable smoke test

On a clean or isolated Windows environment:

- launch `ContextVault.exe`;
- confirm UI opens;
- confirm runtime resources load;
- confirm no missing DLL, PYD, or resource errors;
- launch managed Chrome;
- complete one validated export;
- close cleanly.

## Gate 10: Release page review

Confirm:

- title: `ContextVault v0.2.0 — Export Reliability and Stability Update`;
- correct tag;
- correct commit;
- release notes;
- ZIP asset;
- checksum asset;
- no private runtime data;
- no draft or prerelease state unless intentional.

## Final decision

Release status is **GO** only when all mandatory gates are supported by evidence.

Source CI success alone is not a complete executable release.
