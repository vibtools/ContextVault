# Internal API and Module Boundaries

ContextVault does not currently promise a stable third-party Python API. This document describes internal responsibilities for contributors and maintainers.

## Application entry points

### `src/app.py`

Repository launcher.

### `src/app/application.py`

Creates the application graph, UI, services, controller, browser worker, and shutdown flow.

## Controller layer

### `src/controllers/application_controller.py`

Public workflow boundary used by the UI.

Responsibilities include launching and connecting Chrome, scanning and opening conversations, starting export tasks, preventing conflicting browser workflows, managing archives, loading/saving settings, exposing status/notifications, and coordinating shutdown.

The controller must not expose Playwright objects to the UI.

## Task layer

### `src/core/task_manager.py`

Owns managed background tasks, cancellation, snapshots, progress, completion callbacks, and executor coordination.

Completion callbacks are used to release workflow leases safely after success, failure, or cancellation.

## Browser layer

### `src/browser/session_worker.py`

Dedicated browser command lane and asyncio-loop owner.

Provides serialized command execution and browser-worker lifecycle management.

### `src/browser/browser_manager.py`

Owns Chrome/Playwright behavior:

- profile resolution;
- launch and CDP connection;
- sidebar scan;
- conversation navigation;
- readiness observation;
- virtualized history scan;
- message checkpoint callback;
- authenticated resource retrieval;
- browser refresh and close.

No external thread may directly call Playwright objects created here.

## Parser layer

### `src/parsers/conversation_parser.py`

Transforms stabilized ChatGPT HTML fragments into typed records.

Responsibilities include message container detection, role and source identity, text/Markdown/HTML, code, images, attachments, tables, citations, timestamps/provenance, favicon filtering, and final conversation assembly.

## Export pipeline

### `src/core/export_pipeline.py`

Coordinates one conversation export:

1. load settings and source metadata;
2. open and deeply scan the conversation;
3. persist or consume incremental checkpoints;
4. build typed conversation data;
5. download enabled assets with explicit resource kinds;
6. build and validate the archive;
7. publish;
8. record history and warnings;
9. clean checkpoints and staging.

## Incremental checkpoints

### `src/core/message_checkpoint.py`

Provides atomic message checkpoint storage and verification.

Checkpoints include message JSON and exact code bytes. Failure paths are explicit, and degraded records can upgrade if later verification succeeds.

## Archive building

### `src/core/archive_builder.py`

Writes the staging archive, generated documents, assets, logs, hashes, and final publication.

Temporary files use short same-directory names to reduce Windows path risk.

Final publish naming resolves collisions atomically.

### `src/core/archive_validator.py`

Recomputes structural and integrity evidence.

Validation warnings are distinct from errors.

## RAG generation

### `src/core/rag_builder.py`

Generates retrieval-oriented documents while preserving message order and archive references.

## Models

### `src/models/`

Pydantic models define serialization contracts for settings, conversation/message records, archive/validation records, task/progress records, and export history.

Model aliases preserve camelCase JSON.

## Services

- `config_service.py`: loads, validates, recovers, and saves settings.
- `history_service.py`: stores bounded export history.
- `logging_service.py`: configures queue-backed logging.
- `archive_service.py`: lists, validates, rebuilds summaries, and safely deletes archives.

## Utilities

Shared helpers provide safe paths, Windows filenames, atomic JSON writes, bounded replacement retry, timestamps, and SHA-256 hashing.

## Compatibility rules

An internal change must preserve:

- UI/browser separation;
- one browser worker owner;
- cooperative cancellation;
- settings compatibility;
- archive schema behavior;
- safe paths;
- atomic publication;
- deterministic serialization;
- test coverage;
- public documentation.

## Extension guidance

Before adding an internal API:

1. identify the owning layer;
2. define typed input and output;
3. avoid returning browser objects;
4. define cancellation;
5. define logging and errors;
6. define security constraints;
7. add tests;
8. update documentation.

## Not a public SDK

External tools should consume published archive files rather than import ContextVault internals unless they accept source-level compatibility risk.
