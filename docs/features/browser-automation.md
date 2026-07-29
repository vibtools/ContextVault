# Browser Automation

All Chrome and Playwright objects live on one dedicated browser worker and asyncio event loop. UI and general worker threads communicate through commands and futures; they never touch Playwright objects directly.

ContextVault supports:

- launching official Google Chrome Stable with a ContextVault-owned persistent user-data directory;
- honoring an explicitly configured **non-standard** Chrome user-data root and profile;
- connecting to a user-started Chrome CDP endpoint;
- scanning conversation links;
- opening a conversation;
- progressive scrolling until message count and document height stabilize;
- authenticated retrieval of HTTP, data, and blob resources;
- graceful browser status, refresh, and close operations.

## Launch semantics

**Launch Chrome** never automates Chrome's regular daily-browsing `User Data` directory. When the setting is blank—or when that regular directory is selected—ContextVault uses `data/chrome-user-data` and creates the selected profile there. This produces a separate Chrome process/window, avoids Chrome's process-singleton collision, and preserves manual ChatGPT login across application restarts.

**Connect** remains an explicit CDP workflow. It does not serve as an automatic fallback for a failed profile launch because a normal Chrome process is not necessarily exposing a debugging endpoint.

Selectors are centralized and include fallback strategies because ChatGPT's DOM may change. A selector failure is reported without silently inventing content.
