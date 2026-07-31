# Contributing to ContextVault

Thank you for contributing to ContextVault.

Contributions may include bug fixes, tests, documentation, accessibility improvements, security hardening, performance work, or carefully reviewed feature proposals.

ContextVault prioritizes correctness, data integrity, stability, maintainability, and reproducible Windows releases.

## Read before changing code

Review the public documentation that applies to your work:

- [Architecture](docs/developer/architecture.md)
- [Implementation compliance](docs/developer/implementation-compliance.md)
- [Requirements traceability](docs/developer/requirements-traceability.md)
- [Browser automation](docs/features/browser-automation.md)
- [Archive format](docs/features/archive-format.md)
- [Release process](docs/developer/release-process.md)
- [Security policy](SECURITY.md)

The public documentation under `docs/` is the source of truth for public behavior and contribution requirements.

## Supported technology stack

ContextVault currently uses Python 3.12, CustomTkinter, Playwright, Google Chrome Stable, Pydantic, Beautiful Soup, Markdownify, Pillow, Tenacity, Nuitka OneDir, and GitHub Actions on Windows.

Replacing a core technology, changing the archive schema, changing the browser ownership model, or altering the portable runtime layout requires prior maintainer approval.

## Development setup

```powershell
git clone https://github.com/vibtools/ContextVault.git
cd ContextVault

py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.lock
```

Do not run `playwright install`. ContextVault uses Google Chrome Stable installed on Windows.

## Create a focused branch

Examples:

```text
fix/image-readiness
fix/archive-collision
docs/upgrade-guide
test/browser-worker-cancellation
perf/checkpoint-processing
```

Avoid mixing unrelated changes in one pull request.

## Required local checks

Run these before opening a pull request:

```powershell
python scripts/test/check_environment.py --skip-chrome
python scripts/test/run_tests.py
python -m compileall -q src tests
git diff --check
```

For browser behavior changes, also test with a real ContextVault-managed Chrome profile on Windows.

For build or packaging changes, run:

```powershell
python -m pip install -r requirements.lock -r requirements-build.lock
python scripts/test/check_environment.py
python scripts/test/run_tests.py
python scripts/build/build_windows.py
python scripts/release/package_release.py
```

## Architecture rules

### UI thread

Do not perform browser automation, parsing, archive generation, network retrieval, or heavy filesystem operations directly on the UI thread.

### Browser ownership

All Playwright and Chrome objects must remain on the dedicated browser worker and its asyncio event loop.

### Export integrity

Do not weaken per-message checkpointing, exact code-byte preservation, archive validation, safe path checks, atomic publication, warning propagation, or cancellation cleanup.

### Public archive compatibility

Additive metadata may be introduced only with corresponding models, schemas, validation, tests, and documentation. Breaking archive-format changes require an explicit schema-version decision.

### Dependencies

A new dependency must be justified, maintained, license-compatible, Windows-compatible, Nuitka-compatible, and pinned consistently.

## Coding expectations

- Preserve existing features and backward compatibility unless a breaking change is approved.
- Use type hints.
- Use `pathlib` for filesystem paths.
- Avoid hardcoded developer-specific paths.
- Handle exceptions explicitly.
- Do not silently ignore failures.
- Keep logs useful without exposing credentials or session secrets.
- Remove unused imports, dead code, debug statements, and temporary files.
- Add regression tests for fixed defects.
- Keep browser selectors centralized and provide evidence for selector changes.

## Documentation expectations

Update documentation when changing user-visible behavior, settings, requirements, archive files, browser behavior, upgrade behavior, known limitations, security, privacy, or release procedures.

At minimum, consider:

```text
README.md
README.txt
CHANGELOG.md
docs/
```

Do not refer public contributors to unavailable private files.

## Commit messages

Use clear, descriptive messages. Conventional prefixes are encouraged:

```text
fix: bound stalled image readiness
docs: add v0.2.0 upgrade guide
test: cover duplicate export submission
security: harden archive path validation
build: verify packaged runtime assets
```

## Pull request contents

A good pull request explains the problem, root cause, implementation, compatibility, tests, security, performance, documentation, and remaining limitations.

Use the repository pull request template.

## Security issues

Do not include vulnerability details in a public issue or pull request. Follow [SECURITY.md](SECURITY.md).

## Personal and runtime data

Never commit:

```text
data/chrome-user-data/
data/settings.json
data/export_history.json
data/checkpoints/
exports/
logs/
*.partial-*
*.invalid-*
.cv-*.tmp
```

Before sharing logs, remove conversation titles, URLs, local paths, cookies, tokens, and personal content.

## Review criteria

Reviewers evaluate correctness, regression risk, browser thread ownership, archive integrity, Windows behavior, error handling, security, performance, dependency impact, tests, documentation, and build compatibility.

## Community conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contribution may be distributed under the project's MIT License.
