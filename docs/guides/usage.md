# Usage Guide

This guide explains the complete normal workflow without requiring development knowledge.

## Application pages

### Dashboard

Shows the current application, browser, task, and archive state.

### Conversations

Scans ChatGPT conversations, allows selection, and starts export.

### Archives

Lists completed archives and provides actions such as open folder, open Markdown, validate, rebuild summary, or delete.

### Export History

Shows recent export results and paths.

### Settings

Configures browser profile, export behavior, assets, and performance.

### Logs

Displays diagnostic events. Use this page when an operation fails or completes with warnings.

### About

Shows application and project information.

## Recommended first-run configuration

Open **Settings** and use:

```text
Browser Profile Root: blank
Profile: Default
Default Folder: exports
Archive Name: {title}
Overwrite: off
Verify Export: on
Attachments: off
Message Retry Count: 5
Delay Mode: Normal
Memory Mode: Balanced
```

Save settings.

## Launch Chrome

Select **Launch Chrome**.

ContextVault opens a separate official Chrome window using its managed profile. Log in to ChatGPT manually.

The managed profile is reused on later launches.

### When to use Connect

Use **Connect** only when all of the following are true:

- you intentionally started Chrome with remote debugging;
- you used a non-standard user-data directory;
- the configured CDP endpoint is reachable;
- you understand that ContextVault is attaching to an existing browser.

A failed Launch Chrome operation does not automatically fall back to an unrelated Chrome process.

## Scan the conversation list

1. Wait for ChatGPT to load.
2. Return to ContextVault.
3. Open **Conversations**.
4. Select **Scan**.

ContextVault reads conversation links and titles from the ChatGPT sidebar.

The visible sidebar title is the canonical archive title. It does not use the first assistant heading as the conversation title.

## Select conversations

Select one or more items.

Repeated selections of the same conversation are removed before the export queue starts.

## Export

Choose the appropriate export action.

During export:

- one browser workflow owns the Playwright context;
- a second export or conflicting browser operation is rejected rather than interleaved;
- ContextVault opens the conversation;
- it waits for ChatGPT readiness;
- it scans virtualized history;
- it checkpoints stable messages;
- it downloads enabled assets;
- it builds in a staging directory;
- it validates;
- it publishes atomically.

## Large conversations

ChatGPT may keep only a portion of a long conversation in the live DOM. ContextVault scrolls through virtualized history and accumulates verified messages.

There is no single fixed total runtime limit while meaningful progress continues.

A stall timeout applies when no meaningful progress is observed.

## Per-message checkpointing

Before scrolling away from a stable window, ContextVault:

1. extracts visible messages;
2. writes atomic message checkpoints;
3. saves exact code bytes;
4. reads the saved data back;
5. verifies source identity and content;
6. commits the window;
7. continues scrolling.

Completed checkpoints survive one bounded recovery reload during the same export.

## Message retries and degraded messages

If one message fails:

1. ContextVault retries that message according to **Message Retry Count**;
2. it may reload the page once for recovery;
3. previously verified checkpoints remain;
4. after retries are exhausted, visible fallback content can be preserved as a degraded message;
5. the warning is recorded in the archive.

A degraded message is not silently omitted. It includes capture status, attempts, error, source identity, and visible text where available.

A full disk, inaccessible destination, browser termination, or inability to write a valid checkpoint remains fatal.

## Image readiness

A browser image or spinner may never complete.

ContextVault waits according to Delay Mode:

```text
Fast    8 seconds
Normal 20 seconds
Safe   45 seconds
Auto   20 seconds
```

After the grace period, the scan may continue with a warning. Asset retrieval and final validation remain authoritative.

Decorative favicons and known interface images are excluded from conversation image extraction.

## Attachments

Attachments are disabled by default.

When enabled, attachment-specific fallback interaction is used only for attachment resources. An image error does not trigger attachment-control scanning.

Some private, expired, or account-restricted assets may be unavailable.

## Archive naming

The default template is:

```text
{title}
```

Supported tokens include:

```text
{title}
{id}
{date}
```

When two conversations produce the same title and overwrite is off, ContextVault uses a stable conversation-identity suffix. Additional collisions receive a numbered suffix.

Final naming is resolved at publication time to prevent races.

## Overwrite and compression

### Overwrite off

The existing archive is preserved and a distinct destination name is selected.

### Overwrite on

The valid staged archive replaces the target only after successful construction and validation. A failed replacement must preserve the prior valid archive.

### Compression on

ContextVault also creates a ZIP package where supported by the export workflow.

## Cancellation

Cancellation is cooperative.

The task stops at a safe cancellation point, cleans temporary staging/checkpoint data, and reports cancellation rather than a false browser error.

Do not force-close the process unless normal cancellation cannot complete.

## Archive review

After export, open **Archives**.

Review:

```text
conversation.md
metadata.json
manifest.json
logs\export.log
logs\validation.log
```

Use **Validate** before relying on an archive that has been copied, edited, or stored for a long time.

## Rebuild Summary

Rebuild Summary regenerates summary data and updates the related manifest integrity metadata.

It is not a general repair operation for corrupted archives.

## Delete Archive

Deletion is restricted to a direct archive child under the configured archive root. Confirm the selected path before deletion.

## Best practices

- Keep Verify Export on.
- Export to a writable local drive.
- Leave enough disk space for assets and staging.
- Avoid manually editing published archive files.
- Back up important archives.
- Keep ContextVault and its Chrome window open during export.
- Avoid manual navigation or scrolling in the active export tab.
- Review warnings before treating an export as complete.
