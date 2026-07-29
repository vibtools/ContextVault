# Archive Format

Every archive is a self-contained directory with `manifest.json` as its entry point. JSON uses UTF-8 without BOM, four-space indentation, camelCase keys, a root object, and the standard envelope fields `schemaVersion`, `format`, `generatedBy`, `generatedAt`, and `version`.

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

The manifest records SHA-256 and byte size for generated content files. Manifest and log files are deliberately excluded from the hash set to avoid recursive and post-validation mutations. Message references use archive-relative paths and are checked against path traversal. RAG chunks preserve complete message boundaries.
