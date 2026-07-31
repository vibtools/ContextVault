# Configuration

Settings are validated with Pydantic and stored atomically in `data/settings.json`. Invalid settings are preserved with an `.invalid` suffix before defaults are restored. Existing settings files remain compatible; omitted fields receive validated defaults.

## Browser

- **Browser:** fixed to Google Chrome.
- **Browser Profile Root:** optional non-standard Chrome user-data directory. Blank selects ContextVault's persistent isolated root at `data/chrome-user-data`. Chrome's regular daily-browsing `User Data` root is not automated; selecting it is safely redirected to the ContextVault-managed root.
- **Profile:** profile directory name, such as `Default` or `Profile 1`; paths and traversal are rejected. ContextVault creates the selected profile under its managed root when needed.
- **CDP Endpoint:** default `http://127.0.0.1:9222`; used only by the explicit **Connect** action.

## Export

- **Default Folder:** absolute or project-relative destination.
- **Archive Name:** supports `{title}`, `{id}`, and `{date}`.
- **Auto Create Folder, Overwrite, Compress, Verify Export:** control deterministic archive creation.

## Assets

Image, code, table, attachment, summary, and search-index extraction can be controlled. Mandatory core JSON, Markdown, statistics, RAG documents, and logs are always generated.

## Performance

- **Worker Threads:** accepts 1, 2, 4, or 8.
- **Delay:** controls DOM stabilization timing.
- **Memory:** selects the bounded readiness timeout policy.
- **Message Retry Count:** accepts 1–20; default 5. This is the number of retries after the initial per-message capture attempt. ContextVault retries only the failed message/window, performs at most one recovery reload per failed key while retaining completed checkpoints, resumes scanning, and then preserves the exhausted message as a clearly marked degraded placeholder. It does not silently remove the message or publish an invalid code file.

A degraded message records `captureStatus`, `captureAttempts`, `captureError`, source identity, capture time, and visible fallback text in `conversation.json`. The archive manifest and metadata record the degraded count and warnings. Infrastructure failures such as a full disk, inaccessible export directory, browser termination, or corrupt archive publication remain fatal because continuing would not be safe.
