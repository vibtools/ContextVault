# Changelog

All notable public changes to ContextVault are documented in this file.

ContextVault follows Semantic Versioning for the application. The archive schema has its own version and remains `1.0` in application version `0.2.0`.

## [Unreleased]

No unreleased public changes are documented yet.

## [0.2.0] - 2026-07-31

### Summary

ContextVault 0.2.0 is an export reliability and stability release focused on large conversations, browser-rendered images, Windows filesystem behavior, export concurrency, archive naming, and diagnostics.

### Added

- Incremental per-message checkpointing before upward scrolling.
- Atomic checkpoint JSON persistence and immediate round-trip verification.
- Exact UTF-8 code-byte checkpointing and validation.
- Message-specific retry with configurable `Message Retry Count`.
- One bounded recovery reload while preserving completed checkpoints.
- Explicit degraded-message preservation after configured retries are exhausted.
- Capture status, attempt count, error, source identity, capture time, and timestamp provenance metadata.
- Canonical sidebar-title preservation for archive naming.
- Stable conversation-identity suffixes for duplicate archive titles.
- Exclusive browser workflow gating for export, scan, open, refresh, launch, connect, and close operations.
- Publish-time atomic archive collision resolution.
- Bounded recovery for a stable zero-message conversation shell.
- Bounded browser image-render grace by delay mode.
- Stalled-image warnings propagated to export metadata and logs.
- Regression tests for large-conversation progress, image spinners, export exclusivity, title handling, cancellation, and Windows temporary path behavior.
- Public upgrade, privacy, release verification, limitations, support, security, and release-process documentation.
- An isolated `.venv-release` verifier that installs exact locked dependencies without modifying the global Python environment.

### Fixed

- Removed the fixed 900-second total export deadline while meaningful scan progress continues.
- Changed readiness timeout behavior to detect a true no-progress stall instead of total elapsed export time.
- Prevented a permanently broken or stalled image from blocking virtualized scrolling forever.
- Separated image-loading indicators from blocking ChatGPT loading indicators.
- Prevented spinner-only DOM churn from resetting semantic message stabilization indefinitely.
- Filtered decorative favicon and interface images from conversation image extraction.
- Restricted ChatGPT attachment-control fallback to actual attachment resources.
- Prevented image HTTP errors from triggering a 180-second attachment-control scan.
- Removed unnecessary top-reset/down-scan behavior caused by misrouted image assets.
- Prevented duplicate export workflows from interleaving one shared Playwright context.
- Prevented archive publication races from failing with `FileExistsError`.
- Corrected archive titles that were previously derived from the first assistant heading instead of the sidebar title.
- Added stable archive suffixes when two conversations share the same visible title.
- Replaced long Windows temporary asset names with short same-directory temporary files.
- Hardened atomic JSON replacement against transient Windows sharing denials.
- Corrected exact CRLF/LF code validation by comparing UTF-8 bytes rather than newline-translated text.
- Prevented a stable zero-message DOM from being treated as a complete conversation.
- Added current `data-message-id` message-container compatibility.
- Corrected Launch Chrome profile resolution so a blank or regular Chrome root uses ContextVault's managed profile.
- Removed unsafe automatic fallback from a failed managed launch to an unrelated CDP browser.
- Corrected user cancellation logging so expected interruption is reported at information level rather than as a false browser failure.
- Added ignore rules for browser profiles, checkpoints, logs, partial files, invalid recovery files, and short temporary files.

### Security and privacy

- Documented `data/chrome-user-data` as sensitive local session data.
- Preserved path traversal rejection and safe root containment.
- Preserved direct-child archive deletion restrictions.
- Preserved archive-relative asset validation and SHA-256 integrity checks.
- Prevented personal project documentation and runtime profile data from being included in the public source tree.

### Validation

- Windows GitHub Actions source CI passed on Python 3.12.
- The forensic source suite passed 81 tests.
- JSON/TOML parsing, Python AST validation, repository path checks, dependency synchronization, browser-worker lifecycle, security checks, archive validation, checkpoint recovery, and export exclusivity regressions passed.
- The tag-triggered Windows Nuitka build remains authoritative for the final portable release artifact.

## [0.1.0] - 2026-07-28

### Added

- Initial public Windows desktop application.
- CustomTkinter user interface with Dashboard, Conversations, Archives, Export History, Settings, Logs, and About pages.
- Dedicated Playwright browser worker using Google Chrome Stable.
- Managed persistent Chrome profile and explicit CDP connection workflow.
- Conversation scanning, progressive loading, parsing, asset extraction, archive generation, and archive validation.
- Portable archive files, RAG documents, summaries, statistics, logs, and SHA-256 hashes.
- Settings persistence, export history, task management, cancellation, and notifications.
- Nuitka OneDir build configuration and GitHub Actions workflows.
- Initial public documentation and MIT license.

### Known limitations in 0.1.0

- Large exports could exhaust a fixed readiness deadline.
- Browser-rendered image placeholders could block scrolling.
- Decorative image routing could trigger attachment fallback.
- Concurrent export requests could interleave and collide.
- Version labels in several documents were inconsistent with the public tag.

[Unreleased]: https://github.com/vibtools/ContextVault/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/vibtools/ContextVault/releases/tag/v0.2.0
[0.1.0]: https://github.com/vibtools/ContextVault/releases/tag/v0.1.0
