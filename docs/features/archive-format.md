# Archive Format

Every archive is a self-contained directory with `manifest.json` as its entry point. The frozen folder/file layout is unchanged. JSON uses UTF-8 without BOM, four-space indentation, camelCase keys, a root object, and the standard envelope fields `schemaVersion`, `format`, `generatedBy`, `generatedAt`, and `version`.

```text
archive/
├── manifest.json
├── metadata.json
├── conversation.json
├── conversation.md
├── summary.json
├── search-index.json
├── statistics.json
├── assets/{code,images,attachments,tables,citations}/
├── rag/{chunks,documents,keywords,chunk-map}.json
└── logs/{export,validation}.log
```

## Incremental capture integrity

The final archive layout remains frozen, but export generation now uses a temporary per-message checkpoint store before archive construction:

```text
settled DOM window
    → message extraction
    → atomic message JSON checkpoint
    → exact code-byte checkpoint
    → immediate round-trip verification
    → continue upward scroll
```

Temporary checkpoints are not part of the published archive and are deleted after publication, cancellation, or failure. The final archive is still built in an isolated staging directory and published only after validation.

Code content is compared as exact UTF-8 bytes. Validation does not use universal-newline text conversion, so CRLF and LF code blocks remain lossless and are not falsely reported as mismatches.

## Message status and timestamps

Each message contains ordered `sequenceNumber` plus additive integrity metadata:

- `timestamp`: original message time when a reliable source exposes it; otherwise `null`;
- `capturedAt`: when ContextVault captured the stabilized message window;
- `timestampSource`: `message_timestamp`, `page_state`, `dom_inferred`, or `unknown`;
- `captureStatus`: `verified` or `skipped`;
- `captureAttempts`, `captureError`, `sourceKey`, and `sourceSignature`.

ContextVault never presents capture time as an original message time. Conversation-level start/end times are derived only from reliable message timestamps. If none are available, `conversationStartedAt` and `conversationEndedAt` remain `null`, `timestampSource` is `unknown`, and `exportedAt` still records the actual export time.

`manifest.json`, `metadata.json`, and `conversation.json` contain start/end/export/timezone/provenance fields. Every generated JSON file retains the common `generatedAt` envelope timestamp. The manifest also records total, verified, and degraded message counts, configured retry count, duration when calculable, and whether incremental verification was active.

## Validation and hashes

The manifest records SHA-256 and byte size for generated content files. Manifest and log files are deliberately excluded from the hash set to avoid recursive and post-validation mutations. Message references use archive-relative paths and are checked against path traversal. RAG chunks preserve complete message order, including explicit degraded placeholders. A degraded message is a validation warning, not a silent omission; unrelated structural/hash corruption remains an error.
