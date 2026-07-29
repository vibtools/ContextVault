# Configuration

Settings are validated with Pydantic and stored atomically in `data/settings.json`. Invalid settings are preserved with an `.invalid` suffix before defaults are restored.

## Browser

- **Browser:** fixed to Google Chrome.
- **Browser Profile Root:** optional non-standard Chrome user-data directory. Blank selects ContextVault's persistent isolated root at `data/chrome-user-data`. Chrome's regular daily-browsing `User Data` root is not automated; selecting it is safely redirected to the ContextVault-managed root.
- **Profile:** profile directory name, such as `Default` or `Profile 1`; paths and traversal are rejected. ContextVault creates the selected profile under its managed root when needed.
- **CDP Endpoint:** default `http://127.0.0.1:9222`; used only by the explicit **Connect** action.

## Export

- **Default Folder:** absolute or project-relative destination.
- **Archive Name:** supports `{title}`, `{id}`, and `{date}`.
- **Auto Create Folder, Overwrite, Compress, Verify Export:** control deterministic archive creation.

## Assets and performance

Image, code, table, attachment, summary, and search-index extraction can be controlled. Mandatory core JSON, Markdown, statistics, RAG documents, and logs are always generated. Worker threads accept 1, 2, 4, or 8.
