# Archive Format

ContextVault archives are portable directories with deterministic JSON, readable Markdown, assets, RAG documents, logs, and integrity metadata.

The application version in this release is `0.2.0`. The archive schema remains `1.0`.

## Directory layout

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

## JSON conventions

Generated JSON uses:

- UTF-8 without BOM;
- four-space indentation;
- camelCase keys;
- a root object;
- ISO 8601 timestamps where applicable;
- archive-relative paths;
- explicit schema and generator metadata.

Common envelope fields include:

```text
schemaVersion
format
generatedBy
generatedAt
version
```

## `manifest.json`

The manifest is the archive entry point.

It records archive identity, application and schema versions, source conversation identity, message counts, verified and degraded counts, capture warnings, generated paths, SHA-256 values, byte sizes, export/validation status, and timing/provenance fields.

The manifest does not hash itself because self-hashing would be recursive. Logs may also be excluded from the immutable content hash set when they are finalized after validation.

## `metadata.json`

Contains descriptive and capture metadata such as title, source URL and conversation ID, export time, conversation start/end times when reliable, timezone/provenance, warning summaries, enabled assets, retry information, and verification information.

## `conversation.json`

Contains the ordered message collection.

Message records can include:

```text
sequenceNumber
role
text
markdown
html
timestamp
timestampSource
capturedAt
captureStatus
captureAttempts
captureError
sourceKey
sourceSignature
code
images
attachments
tables
citations
parentMessageId
childMessageId
```

Exact available fields depend on message content and source data.

### Timestamp rules

ContextVault separates source time from capture time.

- `timestamp` is used only when a reliable source exposes the message time.
- `capturedAt` is the time ContextVault captured the stable message window.
- missing source timestamps remain `null`;
- conversation start/end times are not invented.

### Capture status

A message is normally:

```text
verified
```

After exhausted retries, a message can be:

```text
skipped
```

The skipped/degraded record preserves visible fallback content, order, source identity, attempts, and error information where possible.

## `conversation.md`

Human-readable Markdown representation of the conversation.

It preserves message order and references exported assets.

A degraded message is clearly marked rather than silently removed.

## `summary.json`

Contains summary-oriented metadata.

The Archives page can rebuild summary data. Rebuild Summary updates the related manifest integrity metadata.

## `search-index.json`

Contains deterministic search-oriented data for local or external tools.

## `statistics.json`

Contains counts and size/role/content statistics derived from the archive.

## Assets

### Code

Code blocks are saved under:

```text
assets\code\
```

ContextVault validates exact UTF-8 bytes. CRLF and LF are not normalized during integrity comparison.

### Images

Conversation images are stored under:

```text
assets\images\
```

Known decorative favicon and interface images are not treated as conversation content.

### Attachments

Optional attachments are stored under:

```text
assets\attachments\
```

Attachments are disabled by default.

### Tables

Structured table data is stored under:

```text
assets\tables\
```

### Citations

Citation metadata and related resources are stored under:

```text
assets\citations\
```

## RAG documents

The `rag/` directory contains retrieval-oriented representations:

- `chunks.json`
- `documents.json`
- `keywords.json`
- `chunk-map.json`

RAG output preserves message order and includes explicit degraded-message representation.

ContextVault does not bundle an embedding model or vector database.

## Incremental checkpointing

Temporary checkpoints are used during export but are not part of the published archive.

Flow:

```text
stable DOM window
→ extract message fragment
→ write atomic checkpoint JSON
→ save exact code bytes
→ read back and verify
→ commit message signature
→ continue upward scroll
```

Checkpoints are stored under a temporary data path and removed after successful publication, cancellation, or failure.

## Staging and publication

A final archive is constructed in an isolated staging directory.

ContextVault:

1. writes required files;
2. downloads enabled assets;
3. generates indexes and RAG data;
4. validates;
5. selects the final publish name;
6. publishes atomically.

A failed build must not replace a previously valid archive.

## Duplicate names

When overwrite is off:

1. ContextVault prefers the canonical title;
2. a stable conversation-ID suffix is used for a title collision;
3. a numbered suffix is used for an additional collision.

Name selection is finalized during publication to prevent concurrent races.

## Validation

Validation recomputes and checks:

- required files and directories;
- JSON structure and schemas;
- message order;
- parent/child links;
- character and content counts;
- asset paths;
- file sizes;
- SHA-256 values;
- code bytes;
- table data;
- RAG counts and mappings;
- search-index references;
- path traversal and root containment.

A capture warning is not the same as structural corruption.

## Portability

Archive paths are relative and Windows-safe. Files can be copied to another system, but external tools must preserve filenames and bytes.

Manual edits can invalidate hashes and references.
