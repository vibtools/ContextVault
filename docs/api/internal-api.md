# Internal API

The public internal boundaries are intentionally narrow.

## `ApplicationController`

UI-safe methods: `launch_browser`, `connect_browser`, `open_conversation`, `scan_conversations`, `export_conversations`, `cancel_export`, `resume_export`, settings/history/archive operations, and `shutdown`. Heavy work is submitted to `TaskManager`.

## `BrowserSessionWorker`

Owns the browser lane and accepts serialized commands. `BrowserManager` is not called from UI code.

## `ConversationParser`

`parse(html, url, title, exported_at)` returns a validated `ConversationRecord` with ordered messages and extracted references.

## `ArchiveBuilder` and `ArchiveValidator`

`ArchiveBuilder.build(...)` writes to an isolated staging directory, validates, atomically publishes, and optionally compresses. `ArchiveValidator.validate(path)` checks required structure, Pydantic schemas, message sequencing, asset references, hashes, and sizes.

## Model contract

All external JSON serialization uses Pydantic aliases and camelCase. Python APIs use snake_case.
