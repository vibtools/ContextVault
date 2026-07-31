# Browser Automation

ContextVault uses Playwright with official Google Chrome Stable.

The browser architecture is intentionally serialized: one dedicated browser worker owns all Chrome and Playwright objects.

## Supported workflows

ContextVault can:

- launch a managed persistent Chrome profile;
- launch an explicitly configured non-standard profile root;
- connect to an intentionally remote-debugging-enabled Chrome instance;
- scan ChatGPT sidebar conversations;
- open a selected conversation;
- observe loading, streaming, messages, and virtualized history;
- checkpoint messages before scrolling;
- retrieve authenticated resources;
- refresh or close the managed browser;
- report status and cancellation.

## Dedicated browser ownership

Playwright objects are not thread-safe across arbitrary application threads.

Architecture:

```text
UI
→ ApplicationController
→ TaskManager
→ BrowserSessionWorker
→ one asyncio loop
→ Playwright
→ Google Chrome
```

The UI and general workers exchange commands, futures, and plain data. They do not directly manipulate browser objects.

## Exclusive workflows

A complete browser workflow receives an exclusive lease.

This prevents operations such as two exports, export and scan, export and refresh, export and close, or launch and connect from interleaving one shared browser context.

A duplicate export request is rejected before it can change the active conversation or archive state.

The lease is released after success, failure, or safe cancellation cleanup.

## Managed profile

With Browser Profile Root blank, ContextVault uses:

```text
data\chrome-user-data
```

Benefits include a separate Chrome process, reusable ChatGPT login, isolation from normal daily browsing, and predictable automation ownership.

ContextVault does not automate the regular Chrome `User Data` root.

## Explicit custom profile

An advanced user can configure a non-standard user-data root and a profile directory name.

The profile directory field accepts a name, not a path.

## Connect over CDP

**Connect** is advanced.

It requires Chrome to be started intentionally with remote debugging and an appropriate non-standard profile.

ContextVault does not automatically attach to any Chrome process after a managed launch failure.

## Conversation title

The canonical archive title comes from the scanned ChatGPT sidebar entry.

Preference order includes stable full-title attributes before truncated visible text.

Accessibility labels can contain project or UI context; that context is removed rather than used as the archive title.

The first assistant heading is not used as the conversation title.

## Readiness observation

The browser installs an observer that tracks meaningful state, including:

- message containers;
- streaming state;
- blocking loaders;
- image loaders;
- continue-generation controls;
- scroll position;
- message content and asset counts;
- DOM semantic stability.

Readiness does not complete with zero messages.

## Empty conversation recovery

A page can display a stable shell before React renders messages.

ContextVault waits for meaningful state. If the DOM remains idle with zero messages for the bounded recovery period, it reloads once.

If messages still do not appear, it raises a readiness error rather than exporting an empty archive.

## Progress-based stall policy

A long conversation can legitimately exceed a fixed wall-clock duration.

ContextVault measures meaningful progress, such as new message keys, changed committed count, scroll movement, checkpoint activity, transition toward the top, and resolved recovery state.

The operation can continue beyond the nominal stall duration while progress occurs.

A no-progress stall still fails explicitly.

## Virtualized history

ChatGPT may remove offscreen messages from the live DOM.

ContextVault accumulates verified message records independently of the current viewport. Scrolling continues upward until the complete reachable history is captured.

## Semantic stabilization

Transient spinners can cause frequent DOM mutations without changing message content.

ContextVault compares semantic message state such as source key, role, text, timestamp, and asset counts.

Spinner-only churn does not block a stable message forever.

Meaningful content or asset-count changes still reset stabilization.

## Image readiness

An image is browser-pending while it has not completed loading.

A terminal broken image is not treated as loading forever.

Image-specific indicators are separated from blocking ChatGPT loaders.

Grace periods:

```text
Fast    8 seconds
Normal 20 seconds
Safe   45 seconds
Auto   20 seconds
```

After the grace period, ContextVault can checkpoint the stable message markup and continue with a warning.

A newly observed image count receives its own bounded wait.

## Asset routing

Resources carry an explicit kind, such as image or attachment.

- image failures do not invoke attachment controls;
- attachment controls are used only for attachments;
- decorative favicon sources are filtered;
- HTTP, data, and blob resources use appropriate authenticated retrieval paths.

## Checkpoint and retry flow

For a stable window:

1. extract each message fragment;
2. write atomic checkpoint JSON;
3. write exact code bytes;
4. read back and validate;
5. commit source signatures;
6. scroll upward.

If a message fails:

1. retry that message;
2. retain the current window where practical;
3. reload once at the recovery threshold;
4. resume with completed checkpoints;
5. preserve an exhausted message as degraded when safe.

## Cancellation

Cancellation is cooperative.

Expected interruption is logged as cancellation at information level. It is not reported as a browser crash.

The browser worker cancels active and queued commands during shutdown and can restart safely where supported.

## Selector maintenance

ChatGPT can change without notice.

Selectors are centralized and use fallbacks. Unsupported DOM states must produce diagnostics and tests; they must not silently invent missing content.
