# Changelog

All notable changes to ContextVault are documented here. The project follows Semantic Versioning and the Keep a Changelog structure.

## [Unreleased]

### Fixed

- Serialized same-target JSON commits and added bounded Windows sharing-denial retries so concurrent atomic writes no longer fail with transient `PermissionError: Access is denied`.
- Corrected Launch Chrome so a blank or regular Chrome profile root resolves to ContextVault's persistent non-standard `data/chrome-user-data` directory instead of forwarding `about:blank` into an already-running daily Chrome process.
- Removed the invalid automatic CDP fallback from Launch Chrome; Connect remains an explicit operation for intentionally remote-debugging-enabled Chrome instances.
- Stopped Playwright from passing its two extension-disabling default arguments to the dedicated persistent profile.

### Validation

- 41 source and regression tests pass, including isolated browser-profile resolution, no-CDP-fallback enforcement, browser-worker lifecycle, repeated-message preservation, opaque attachment detection, deep archive consistency, atomic replacement, and rollback.
- All 124 frozen release-checklist items are explicitly classified PASS or FAIL.
- Official Windows GitHub Actions execution, Nuitka binary generation, and clean Windows 10/11 Chrome-profile smoke testing remain mandatory before a stable public release.

## [1.0.0] - 2026-07-28

### Added

- Complete frozen CustomTkinter one-window desktop UI with Dashboard, Conversations, Archives, Export History, Settings, Logs, and About pages.
- Managed task queue, cooperative cancellation, current-session resume, progress events, notifications, and queue-backed logging.
- Dedicated Playwright browser worker with persistent Google Chrome profile launch, CDP connection, conversation scanning, progressive lazy-load stabilization, and authenticated resource retrieval.
- Lossless BeautifulSoup/Markdownify parser for ordered messages, roles, timestamps, plain text, Markdown, HTML, code, images, attachments, tables, and citations.
- Pydantic domain models and deterministic camelCase JSON envelopes.
- Atomic archive generation with every frozen mandatory document, asset folder, RAG file, export log, validation log, manifest mapping, SHA-256 hashes, and optional ZIP compression.
- Archive validation, archive management, summary rebuild with manifest-integrity refresh, export history, and validated settings recovery.
- Runtime defaults, generated JSON Schemas, dark theme resource, template resources, Windows application icon, and portable README.
- Standard-library forensic test suite and source/environment verification scripts.
- Valid Nuitka configuration, Windows OneDir build script, release ZIP/checksum packager, CI workflow, and tag-triggered GitHub Release workflow.
- Complete installation, usage, configuration, architecture, internal API, troubleshooting, FAQ, release, and requirements-traceability documentation.

### Fixed

- Hardened lazy-loaded sidebar scanning, message-scroll targeting, transient browser retries, restart-safe browser cancellation, platform-independent Chrome profile validation, and x64 Windows drag/drop pointer handling.
- Expanded archive validation to recompute message links/counts, code/table payloads, asset hashes/sizes, search mappings, and RAG consistency.
- Replaced empty packages, empty tests, invalid placeholder scripts, empty documentation index, empty `.gitignore`, and Markdown-wrapped invalid `nuitka.toml`.
- Prevented UI use of private controller browser APIs.
- Made controller shutdown idempotent.
- Corrected conversation search focus and selected-item state handling.
- Preserved archive validity when rebuilding `summary.json` by updating the manifest hash and validation status.

### Security

- Added archive-relative path traversal rejection, safe root containment checks, Windows-safe filename normalization, atomic file publication, direct-child archive deletion restrictions, image integrity verification, and deterministic SHA-256 validation.
