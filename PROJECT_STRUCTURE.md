# ContextVault Project Structure

This document describes the public repository structure for ContextVault 0.2.0.

The public source tree is organized by responsibility. Public behavior, user guidance, architecture, contribution rules, and release procedures are documented under `docs/` and in the root documentation files.

```text
.
├── .github/
│   ├── CODEOWNERS
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
├── assets/
│   ├── fonts/
│   ├── icons/
│   ├── images/
│   └── themes/
├── config/
│   ├── defaults.json
│   └── schemas/
├── data/
│   └── templates/
├── docs/
│   ├── api/
│   ├── configuration/
│   ├── developer/
│   ├── faq/
│   ├── features/
│   ├── getting-started/
│   ├── guides/
│   ├── release-notes/
│   ├── security/
│   └── troubleshooting/
├── examples/
├── scripts/
│   ├── build/
│   ├── dev/
│   ├── maintenance/
│   ├── release/
│   ├── setup/
│   └── test/
├── src/
│   ├── app/
│   ├── browser/
│   ├── config/
│   ├── controllers/
│   ├── core/
│   ├── models/
│   ├── parsers/
│   ├── services/
│   ├── ui/
│   └── utils/
├── tests/
│   └── fixtures/
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── PROJECT_STRUCTURE.md
├── README.md
├── README.txt
├── SECURITY.md
├── SUPPORT.md
├── nuitka.toml
├── pyproject.toml
├── requirements-build.lock
├── requirements.lock
├── requirements.txt
├── run.bat
└── vibproject.ygit
```

## Source responsibilities

### `src/app/`

Application startup and composition root.

### `src/ui/`

CustomTkinter presentation layer. UI modules display state and emit user intent. They must not directly own Playwright objects or perform heavy filesystem work.

### `src/controllers/`

The workflow boundary between UI actions and application services. The controller coordinates tasks, browser operations, exports, archives, settings, history, and shutdown.

### `src/core/`

Business workflows and integrity-critical services, including task management, export orchestration, archive building and validation, RAG generation, incremental checkpoints, atomic publication, and collision handling.

### `src/browser/`

All Google Chrome and Playwright interaction. Browser objects remain on one dedicated worker and asyncio loop.

### `src/parsers/`

Transforms stabilized ChatGPT message HTML into typed conversation records and asset references.

### `src/models/`

Pydantic models and serialization contracts for settings, conversations, archives, tasks, validation, and history.

### `src/services/`

Persistent settings, logging, export history, notifications, and archive-management services.

### `src/utils/`

Shared deterministic helpers such as safe paths, filenames, hashing, timestamps, and JSON writing.

## Configuration and schemas

- `config/defaults.json` contains validated defaults.
- `config/schemas/` contains JSON Schemas for generated and persistent data.
- `nuitka.toml` defines the official Windows OneDir build.
- `requirements.lock` pins runtime dependencies.
- `requirements-build.lock` pins build dependencies.

## Documentation responsibilities

- `README.md`: project overview and beginner quick start.
- `README.txt`: portable package instructions.
- `docs/getting-started/`: installation, quick start, and upgrading.
- `docs/guides/`: detailed usage, limitations, and release verification.
- `docs/configuration/`: settings reference.
- `docs/features/`: browser automation and archive format.
- `docs/security/`: privacy and local-data handling.
- `docs/developer/`: architecture, compliance, traceability, validation, versioning, and release process.
- `docs/release-notes/`: release-specific public notes.

## Runtime directories

The following paths are generated locally and are excluded from public version control:

```text
data\chrome-user-data\
data\settings.json
data\export_history.json
data\checkpoints\
exports\
logs\
build\
artifacts\
```

These paths may contain personal conversation data, authenticated browser state, settings, logs, and release artifacts.

## Public source of truth

The public source of truth is:

1. application source and tests;
2. configuration and schemas;
3. root documentation;
4. documentation under `docs/`;
5. successful GitHub Actions evidence for the relevant commit or tag.

Private maintainer notes are not required to understand, use, build, test, or contribute to the public repository.
