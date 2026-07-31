# Architecture

ContextVault is a Windows desktop application with strict separation between UI, task orchestration, browser automation, parsing, archive generation, persistence, and validation.

## High-level flow

```text
CustomTkinter UI
    ↓ user intent / events
ApplicationController
    ↓ managed task
TaskManager / ThreadPoolExecutor
    ↓ exclusive browser workflow
BrowserSessionWorker
    ↓ one asyncio event loop
BrowserManager / Playwright / Google Chrome
    ↓ stabilized fragments and checkpoints
ConversationParser
    ↓ typed conversation records
ExportPipeline
    ↓ staging
ArchiveBuilder / RagBuilder
    ↓ validation
ArchiveValidator
    ↓ atomic publication
Portable ContextVault archive
```

## Design goals

- UI responsiveness
- one owner for Playwright objects
- deterministic serialization
- incremental capture integrity
- explicit warnings and failures
- Windows-safe filesystem behavior
- backward-compatible archive layout
- safe cancellation and cleanup
- release reproducibility

## UI layer

The CustomTkinter UI renders pages and state, receives queue events, invokes controller operations, and does not directly use Playwright or perform export work on the UI thread.

## Controller layer

The controller validates user intent, starts managed tasks, acquires browser workflow leases, coordinates services, maps progress to UI events, and exposes browser, export, archive, settings, history, and shutdown operations.

## Task manager

The task manager provides centralized executor ownership, task IDs and snapshots, progress, cooperative cancellation, completion callbacks, and bounded lifecycle management.

A completion callback releases the browser workflow lease only after the running work has stopped.

## Browser worker

The browser worker owns one background thread, one asyncio event loop, a serialized command queue, and all Playwright or Chrome objects.

Commands can be cancelled during shutdown. Expected interruption is logged as cancellation.

## Browser workflow gate

A lease spans the complete composite operation, not just one low-level browser command.

This prevents a sequence such as open → load → parse → assets from being interleaved with another export.

## Readiness observer

The browser-side observer reports plain data:

- messages;
- source keys;
- roles;
- semantic signatures;
- loading and streaming state;
- image-loading state;
- continue-generation controls;
- scroll position;
- top and bottom state.

Python applies bounded policy and checkpoint coordination.

## Incremental accumulator

The accumulator retains messages that ChatGPT virtualizes out of the live DOM.

It tracks stable source identity, committed signatures, pending and retry state, image wait state, progress timestamps, and warnings.

Stale offscreen image counts do not permanently block later windows.

## Checkpoint store

Each verified message is written before scroll continuation.

Properties include atomic JSON, exact code-byte files, read-back verification, source signature, retry metadata, degraded-state support, and cleanup after a terminal task state.

## Parser

The parser handles current and fallback ChatGPT message containers.

It extracts role and order, text, Markdown, HTML, timestamps, code, images, attachments, tables, and citations.

Decorative image sources are filtered.

## Export pipeline

The pipeline uses the scanned conversation title as canonical metadata.

It carries explicit resource kind to asset download, merges capture warnings deterministically, and cleans checkpoint data on success, failure, and cancellation.

## Archive builder

The builder writes into staging.

It uses Windows-safe normalized names, root containment, short temporary files, deterministic JSON, required directory creation, stable collision candidates, and atomic publication.

## Archive validator

The validator recomputes evidence rather than trusting generated values.

Warnings do not hide errors.

## Persistence

Settings and history use atomic JSON writes.

Same-target writes are serialized and transient Windows replacement denials receive bounded retry.

## Security boundaries

- untrusted paths are normalized and contained;
- archive references are relative;
- deletion is restricted;
- credentials are not collected;
- Chrome profile data remains local;
- public source excludes runtime data;
- asset kind controls fallback behavior.

## Performance

- browser work is serialized for correctness;
- non-browser work uses bounded worker threads;
- virtualized messages are checkpointed incrementally;
- semantic stability avoids spinner-only churn;
- meaningful progress avoids false total-time failures;
- memory mode controls bounded policy.

## Compatibility

Application version 0.2.0 preserves archive schema 1.0.

Breaking schema changes require an explicit schema version, model/schema updates, migration plan, validator changes, tests, and public documentation.
