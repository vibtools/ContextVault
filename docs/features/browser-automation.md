# Browser Automation

All Chrome and Playwright objects live on one dedicated browser worker and asyncio event loop. UI and general worker threads communicate through commands, plain-data callbacks, and futures; they never touch Playwright objects directly.

ContextVault supports:

- launching official Google Chrome Stable with a ContextVault-owned persistent user-data directory;
- honoring an explicitly configured **non-standard** Chrome user-data root and profile;
- connecting to a user-started Chrome CDP endpoint;
- scanning conversation links;
- opening a conversation;
- MutationObserver-backed readiness detection and progressive virtualized-history scanning;
- per-window message checkpointing before scroll continuation;
- message-specific retry, at most one recovery reload per failed key, and checkpoint resume;
- authenticated retrieval of HTTP, data, and blob resources;
- graceful browser status, refresh, and close operations.

## Launch semantics

**Launch Chrome** never automates Chrome's regular daily-browsing `User Data` directory. When the setting is blank—or when that regular directory is selected—ContextVault uses `data/chrome-user-data` and creates the selected profile there. This produces a separate Chrome process/window, avoids Chrome's process-singleton collision, and preserves manual ChatGPT login across application restarts.

**Connect** remains an explicit CDP workflow. It does not serve as an automatic fallback for a failed profile launch because a normal Chrome process is not necessarily exposing a debugging endpoint.

## Deep-scan and checkpoint flow

For every stable virtualized DOM window, ContextVault executes:

1. observe message/streaming/loading/image state;
2. extract each visible message fragment;
3. atomically save and round-trip-validate its checkpoint JSON;
4. save every code block as exact UTF-8 bytes and read it back;
5. commit message signatures;
6. scroll upward only after the window is committed.

Already committed messages remain in the process-local accumulator and checkpoint store even if ChatGPT virtualizes them out of the live DOM. If one message fails, the current window remains in place while that message is retried. At the recovery threshold the page reloads at most once for that failed key/group; previously completed checkpoints remain intact, the scan resumes, and only uncommitted message keys are retried. After the configured retries are exhausted, visible content for that message is preserved as a degraded placeholder and scanning continues.

The scan cannot complete until every accumulated message key is either verified or explicitly degraded. A browser/session loss, storage failure, or inability to preserve even a degraded placeholder remains an explicit failure.

Selectors are centralized and include fallback strategies because ChatGPT's DOM may change. A selector failure is reported without silently inventing content.
