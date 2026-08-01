<p align="center">
  <img src="assets/images/GitHub-README-hero-banner.png" alt="ContextVault — Preserve AI Context. Forever." width="100%">
</p>

# ContextVault

[![CI](https://github.com/vibtools/ContextVault/actions/workflows/ci.yml/badge.svg)](https://github.com/vibtools/ContextVault/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/vibtools/ContextVault?display_name=tag)](https://github.com/vibtools/ContextVault/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6)](docs/getting-started/installation.md)

**ContextVault v0.2.1** is a Windows desktop application that saves fully loaded ChatGPT conversations as portable, integrity-checked, RAG-ready archives.

It is designed for people who want a dependable local copy of important AI conversations without manually copying messages one by one. You do not need to be a developer to use the portable Windows release.

> **Application version:** 0.2.1
> **Archive schema version:** 1.0
> These versions describe different things. The application can receive bug fixes without changing the archive format.

## What ContextVault does

ContextVault opens a separate Google Chrome window, uses the ChatGPT session that you log into manually, scans your conversation list, loads a selected conversation, and exports its content to a local folder.

A completed archive can include:

- ordered user and assistant messages;
- Markdown, HTML, and plain text;
- code blocks preserved as exact UTF-8 bytes;
- images, tables, citations, and optional attachments;
- conversation metadata and timestamps when ChatGPT exposes them reliably;
- search indexes, statistics, summaries, and RAG documents;
- SHA-256 hashes and validation logs;
- explicit warnings when a message or browser-rendered image could not be captured perfectly.

ContextVault does **not** ask for your ChatGPT password. Login happens directly inside the Chrome window.

## What is improved in v0.2.1

Version 0.2.1 is a cumulative export-reliability hotfix. It preserves archive schema `1.0` while correcting the live failure modes discovered during long-conversation validation:

- virtualized scans recover from permanent DOM mutation churn, persistent non-semantic loaders, and no-op scroll attempts;
- stalled-image handling remains bounded without regressing the established image-scroll fast path;
- active nested scroll containers are selected instead of unrelated document fallbacks;
- transient Playwright observation failures retry in place without discarding accumulated checkpoints;
- mixed ChatGPT message-container families and nested message identity/role attributes are preserved;
- checkpoint storage failures remain fatal instead of being misclassified as degraded messages;
- failed browser workflows release their exclusive lease before terminal state publication, so immediate retry is safe;
- packaged runtime-root and shipped-defaults validation is stricter;
- Windows release builds use a deterministic low-memory Nuitka policy (`LTO` disabled, one compiler job) to prevent MSVC `C1002` heap exhaustion.

See [v0.2.1 release notes](docs/release-notes/0.2.1.md) for the complete change list.

## Requirements

### Portable Windows release

- Windows 10 or Windows 11, 64-bit
- Google Chrome Stable
- A ChatGPT account that you can log into manually
- Enough free disk space for the exported conversation and its assets

Python is **not** required for the portable release.

### Running from source

- Windows 10 or Windows 11, 64-bit
- Python 3.12
- Google Chrome Stable
- Dependencies from `requirements.lock`

ContextVault uses the installed Google Chrome channel. Do not run `playwright install`; the project does not use a bundled Chromium browser.

## Download and run the portable release

1. Open the repository's **Releases** page.
2. Download both files:
   - `ContextVault-Windows-x64.zip`
   - `ContextVault-Windows-x64.zip.sha256`
3. Verify the checksum by following [Release verification](docs/guides/release-verification.md).
4. Extract the complete ZIP to a normal folder such as:
   ```text
   C:\Apps\ContextVault
   ```
5. Do not run the application from inside the ZIP.
6. Open the extracted folder and run:
   ```text
   ContextVault.exe
   ```

Keep the complete extracted folder together. Do not move only the EXE away from its runtime files.

## First export: beginner-friendly steps

### 1. Open Settings

For the safest first run:

- leave **Browser Profile Root** blank;
- keep **Profile** as `Default`;
- keep **Verify Export** enabled;
- keep **Attachments** disabled unless you specifically need them;
- keep **Delay Mode** as `Normal`;
- keep **Message Retry Count** as `5`.

When Browser Profile Root is blank, ContextVault creates its own reusable Chrome profile under:

```text
data\chrome-user-data
```

This is separate from your normal daily Chrome profile.

### 2. Select Launch Chrome

Choose **Launch Chrome** in ContextVault.

A separate official Google Chrome window opens. Log in to ChatGPT manually in that window. ContextVault never asks you to type your ChatGPT credentials into the application.

Use **Connect** only when you intentionally started Chrome with remote debugging. Most users should use **Launch Chrome**.

### 3. Scan conversations

After ChatGPT has loaded:

1. Return to ContextVault.
2. Open the **Conversations** page.
3. Select **Scan**.
4. Wait for the conversation list to appear.

### 4. Select and export

1. Select one or more conversations.
2. Choose **Export Selected** or **Export All**.
3. Leave the ContextVault Chrome window open.
4. Do not manually scroll the active conversation while the export is running.
5. Follow progress in the application and the **Logs** page.

Large conversations may take time. A long runtime is not automatically a failure. ContextVault continues while it detects meaningful progress and stops only when its no-progress policy is exhausted or an unrecoverable error occurs.

### 5. Review the result

Open the **Archives** page to:

- open the generated folder;
- open `conversation.md`;
- validate the archive again;
- rebuild the summary;
- delete an archive you no longer need.

A successful export ends with archive verification and publication. Warnings are preserved in the archive metadata and logs.

## Default settings

| Area | Setting | Default |
|---|---|---:|
| Browser | Browser | Google Chrome |
| Browser | Browser Profile Root | Blank — use managed profile |
| Browser | Profile | `Default` |
| Browser | CDP Endpoint | `http://127.0.0.1:9222` |
| Export | Default Folder | `exports` |
| Export | Archive Name | `{title}` |
| Export | Overwrite | Off |
| Export | Compress | Off |
| Export | Verify Export | On |
| Assets | Images | On |
| Assets | Code | On |
| Assets | Tables | On |
| Assets | Attachments | Off |
| Performance | Worker Threads | 4 |
| Performance | Message Retry Count | 5 |
| Performance | Delay Mode | `Normal` |
| Performance | Memory Mode | `Balanced` |

Read [Configuration](docs/configuration/settings.md) before changing advanced browser or performance options.

## Image-render grace periods

ChatGPT may display an image placeholder or spinner that never finishes rendering in the browser. ContextVault waits for a bounded period before continuing the deep scan:

| Delay mode | Image-render grace |
|---|---:|
| Fast | 8 seconds |
| Normal | 20 seconds |
| Safe | 45 seconds |
| Auto | 20 seconds |

Continuing after this warning does not disable archive validation. Actual asset download and archive integrity checks remain authoritative.

## Archive structure

Each export is a self-contained directory:

```text
archive-name/
├── manifest.json
├── metadata.json
├── conversation.json
├── conversation.md
├── summary.json
├── search-index.json
├── statistics.json
├── assets/
│   ├── code/
│   ├── images/
│   ├── attachments/
│   ├── tables/
│   └── citations/
├── rag/
│   ├── chunks.json
│   ├── documents.json
│   ├── keywords.json
│   └── chunk-map.json
└── logs/
    ├── export.log
    └── validation.log
```

The archive format is documented in [Archive format](docs/features/archive-format.md).

## Local data and privacy

ContextVault stores runtime data locally. Important locations include:

```text
data\chrome-user-data\     Reusable authenticated Chrome profile
data\settings.json         Application settings
data\export_history.json   Export history
exports\                   Default archive destination
logs\                      Application logs
```

Treat `data\chrome-user-data` as sensitive. It may contain cookies and authenticated browser session state. Never commit it to Git, upload it publicly, or share it with another person.

Exported conversations may contain private information. Protect and back them up according to your own security requirements.

Read [Privacy and local data](docs/security/privacy-and-local-data.md).

## Upgrading from v0.1.0

Do not overwrite your only copy of local data.

Before replacing an older portable folder, preserve:

```text
data\chrome-user-data\
data\settings.json
data\export_history.json
exports\
```

Then extract v0.2.1 into a new folder and copy back only the personal runtime data you need. See [Upgrading](docs/getting-started/upgrading.md).

## Troubleshooting

Start with [Common issues](docs/troubleshooting/common-issues.md).

Useful rules:

- use **Launch Chrome** for the normal workflow;
- do not select your normal Chrome `User Data` folder;
- do not close the ContextVault Chrome window during export;
- do not replace individual source files inside a portable build;
- upgrade the complete application package when a fix is released;
- keep **Verify Export** enabled;
- review `logs\` and the archive's `logs\export.log` before reporting a problem.

## Run from source

```powershell
git clone https://github.com/vibtools/ContextVault.git
cd ContextVault

py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.lock

python scripts/test/check_environment.py
python scripts/test/run_tests.py
python src/app.py
```

`run.bat` is the supported repository launcher after dependencies are installed.

## Testing and build

For release-candidate verification, use the isolated environment helper:

```powershell
python scripts/release/verify_release_candidate.py --ref main --skip-chrome
```

It creates `.venv-release`, installs the exact locked dependencies, verifies metadata and source integrity, runs all tests, compiles Python files, and checks staged and unstaged diffs. It does not change the global Python environment.

For local Windows Nuitka tooling:

```powershell
python scripts/release/verify_release_candidate.py `
    --ref main `
    --include-build-dependencies

.\.venv-release\Scripts\python.exe scripts/build/build_windows.py
.\.venv-release\Scripts\python.exe scripts/release/package_release.py
```

The official tag-triggered workflow builds and verifies the Windows x64 OneDir package before publishing release assets.

## Documentation

### For users

- [Documentation home](docs/index.md)
- [Quick start](docs/getting-started/quick-start.md)
- [Installation](docs/getting-started/installation.md)
- [Usage guide](docs/guides/usage.md)
- [Settings](docs/configuration/settings.md)
- [Troubleshooting](docs/troubleshooting/common-issues.md)
- [FAQ](docs/faq/index.md)
- [Known limitations](docs/guides/known-limitations.md)
- [Privacy and local data](docs/security/privacy-and-local-data.md)

### For developers and maintainers

- [Architecture](docs/developer/architecture.md)
- [Internal API](docs/api/internal-api.md)
- [Implementation compliance](docs/developer/implementation-compliance.md)
- [Requirements traceability](docs/developer/requirements-traceability.md)
- [Release process](docs/developer/release-process.md)
- [Release validation](docs/developer/release-validation.md)
- [Versioning](docs/developer/versioning.md)

The public documentation under `docs/` is the source of truth for public behavior and contribution requirements.

## Support, security, and contributing

- General support: [SUPPORT.md](SUPPORT.md)
- Security reporting: [SECURITY.md](SECURITY.md)
- Contributions: [CONTRIBUTING.md](CONTRIBUTING.md)
- Community standards: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## License

ContextVault is released under the MIT License. See [LICENSE](LICENSE).
