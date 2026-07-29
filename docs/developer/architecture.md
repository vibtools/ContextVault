# Architecture

## Package responsibilities

- `src/app/`: bootstrap and application lifecycle.
- `src/ui/`: frozen CustomTkinter presentation, navigation, shortcuts, notifications, drag/drop, logs, and status UI.
- `src/controllers/`: UI-safe orchestration and public application commands.
- `src/core/`: managed tasks, export pipeline, archive builder/validator, and RAG generation.
- `src/browser/`: selector definitions, Playwright browser manager, dedicated browser worker, and asyncio ownership.
- `src/parsers/`: lossless conversation parsing plus deterministic summary/search-index generation.
- `src/models/`: validated domain and external JSON contracts.
- `src/services/`: configuration, logging, history, and archive management.
- `src/utils/`: paths, JSON I/O, security, text, and system integration.

## Execution flow

1. `src/app.py` calls `src.app.application.main`.
2. Logging starts before UI/controller construction.
3. `ApplicationController` loads validated settings and creates one `TaskManager`.
4. `BrowserSessionWorker` reserves one executor lane and owns an asyncio event loop plus `BrowserManager`.
5. UI commands submit controller tasks and return immediately.
6. Browser commands are serialized through the browser worker.
7. Fully loaded HTML is parsed into Pydantic models.
8. `ArchiveBuilder` writes assets and documents into an isolated staging directory.
9. `ArchiveValidator` verifies the archive; publication uses atomic rename.
10. Events, progress, logs, history, and archive updates return to the UI through thread-safe queues.

## Data and trust boundaries

- Browser DOM, URLs, filenames, and downloaded resources are untrusted input.
- Filenames are sanitized and archive references reject absolute paths, traversal, and backslashes.
- Resource bytes are validated where format-specific validation exists, including image verification.
- Settings and archive documents are validated with Pydantic.
- JSON writes are deterministic and atomic.
- Archive deletion is restricted to direct child folders containing a ContextVault manifest.

## Extension points within the frozen architecture

Selector maintenance, parser fallback refinement, additional schema validation, and test fixtures can extend existing modules without changing public boundaries. Cloud services, database persistence, embeddings, alternate browsers, alternate UI frameworks, or architectural migration require a future approved specification and are not version 1.0 extension points.
