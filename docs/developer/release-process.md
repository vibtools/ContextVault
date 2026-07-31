# Release Process

This is the official maintainer process for a ContextVault release.

## 1. Choose the release version

ContextVault uses Semantic Versioning.

For this release:

```text
Application: 0.2.0
Tag: v0.2.0
Archive schema: 1.0
```

Read [Versioning](versioning.md).

## 2. Complete code and documentation

Before release preparation:

- fix all known blockers;
- preserve public functionality;
- add regression tests;
- update user and developer documentation;
- remove references to unavailable private files;
- keep personal runtime data out of Git.

## 3. Synchronize version metadata

Update every application-version location, including:

```text
src/config/constants.py
pyproject.toml
nuitka.toml
README.md
README.txt
CHANGELOG.md
docs/release-notes/<version>.md
vibproject.ygit
schemas containing application-version defaults
```

Do not change archive schema `1.0` merely to match application version `0.2.0`.

## 4. Run local checks in an isolated environment

Do not rely on a shared or global Python installation for release verification. A machine can have newer or older packages than `requirements.lock`, even when the source code is correct.

Run the public-tree boundary check first:

```powershell
python scripts/release/verify_public_tree.py
```

It fails when private maintainer specifications, the release virtual environment, browser profile data, settings, export history, checkpoints, logs, exports, build output, or release artifacts are tracked or staged. It never deletes local files.

Then run the release verifier from the repository root:

```powershell
python scripts/release/verify_release_candidate.py --ref main --skip-chrome
```

The verifier:

1. verifies the public repository privacy boundary before installing anything;
2. locates Python 3.12;
3. creates or repairs `.venv-release`;
4. installs the exact versions from `requirements.lock`;
5. re-verifies the public boundary inside the isolated environment;
6. verifies release metadata;
7. verifies the source environment;
8. runs the complete forensic test suite;
9. compiles `src`, `scripts`, and `tests`;
10. checks both staged and unstaged diffs for whitespace errors.

To recreate the isolated environment from scratch:

```powershell
python scripts/release/verify_release_candidate.py --ref main --skip-chrome --reset
```

To include Nuitka and other locked build tools:

```powershell
python scripts/release/verify_release_candidate.py `
    --ref main `
    --skip-chrome `
    --include-build-dependencies
```

A manual equivalent is:

```powershell
py -3.12 -m venv .venv-release
.\.venv-release\Scripts\python.exe -m pip install -r requirements.lock
.\.venv-release\Scripts\python.exe scripts/release/verify_release_metadata.py --ref main
.\.venv-release\Scripts\python.exe scripts/test/check_environment.py --skip-chrome
.\.venv-release\Scripts\python.exe scripts/test/run_tests.py
.\.venv-release\Scripts\python.exe -m compileall -q src scripts tests
git diff --check
git diff --cached --check
```

During negative-path regression tests, the log may intentionally contain phrases such as `Archive validation failed` or `simulated export failure`. These are expected only when the individual test ends with `ok` and the suite ends with:

```text
Ran 81 tests
OK
```

Review:

```powershell
git status --short
git diff --stat
git diff
```

## 5. Run documentation checks

```powershell
git grep -n -E "project[\\/]" -- "*.md" "*.txt"
git grep -n "1\.0\.0" -- "*.md" "*.txt" "pyproject.toml" "nuitka.toml" "vibproject.ygit"
```

Review every match. Archive schema `1.0` is valid; stale application version `1.0.0` is not.

Verify relative Markdown links.

## 6. Commit and push release preparation

Use this privacy-safe staging sequence. `git rm --cached` removes a path only from the Git index; it does not delete the local private folder.

```powershell
git rm -r --cached --ignore-unmatch -- project
git add -A
python scripts/release/verify_public_tree.py
git diff --cached --check
git status --short
git diff --cached --name-status
```

The following command must produce no output:

```powershell
git ls-files -- project
```

After reviewing the complete staged path list:

```powershell
git commit -m "Prepare ContextVault v0.2.0 release"
git push origin main
```

## 7. Wait for main-branch CI

```powershell
gh run list --workflow ci.yml --branch main --limit 5
gh run watch <RUN_ID> --exit-status
```

Do not tag a failing commit.

## 8. Perform operational smoke tests

Using the exact release-preparation commit:

- launch managed Chrome;
- scan;
- export a small conversation;
- export an image conversation;
- export a long conversation;
- validate;
- test cancellation;
- confirm title and collision naming.

Record evidence.

## 9. Create annotated tag

```powershell
git tag -a v0.2.0 -m "ContextVault v0.2.0 - Export reliability and stability"
git push origin v0.2.0
```

The tag must point to the exact reviewed commit.

## 10. Automatic Build and Release workflow

Tag push starts `.github/workflows/release.yml`.

It checks out the repository, sets up Python 3.12, installs locked dependencies, verifies tag and version metadata, verifies the environment, runs tests, initializes MSVC x64, builds Nuitka OneDir, packages and verifies the ZIP, uploads the workflow artifact, creates the GitHub Release, and attaches the ZIP and checksum.

The workflow reads `docs/release-notes/<version>.md`, uses its first Markdown heading as the release title, and publishes the remaining content as the release description. Do not create the same tag release manually before the workflow runs.

Do not create a conflicting release manually before this workflow when it uses `gh release create`.

## 11. Monitor the workflow

```powershell
gh run list --workflow release.yml --branch v0.2.0 --limit 1
gh run watch <RUN_ID> --exit-status
gh run view <RUN_ID>
```

If it fails, inspect the first failing step.

Do not publish or rename partial artifacts as official releases.

## 12. Verify release assets

Download both assets and follow [Release verification](../guides/release-verification.md).

Extract and perform a portable smoke test.

## 13. Review the release page

Confirm title, tag, target commit, release notes, ZIP, checksum, stable/prerelease status, and absence of private files.

## 14. Post-release checks

- open the release from a logged-out browser;
- download assets;
- verify checksum;
- test documentation links;
- confirm README release badge;
- confirm issue, security, and support links;
- keep workflow logs as evidence.

## 15. Release correction

If the release asset is unsafe or invalid:

1. stop recommending the release;
2. mark it appropriately;
3. investigate;
4. fix source and tests;
5. publish a new patch version.

Do not silently replace a released tag with different source.
