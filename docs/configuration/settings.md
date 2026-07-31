# Settings Reference

ContextVault validates settings with Pydantic and stores them atomically in:

```text
data\settings.json
```

If the settings file is invalid, ContextVault preserves it with an invalid-recovery suffix and restores validated defaults.

The settings schema version is `1.0`.

## Browser settings

### Browser

```text
Chrome
```

Google Chrome is the only supported browser.

### Browser Profile Root

Default:

```text
blank
```

A blank value selects ContextVault's managed persistent root:

```text
data\chrome-user-data
```

This is recommended for most users.

An explicit value must be a non-standard Chrome user-data root intended for ContextVault automation.

Do not select Chrome's regular daily-browsing root:

```text
%LOCALAPPDATA%\Google\Chrome\User Data
```

When a regular Chrome root is detected, Launch Chrome uses the managed ContextVault profile instead of trying to automate the already-running daily Chrome process.

### Profile

Default:

```text
Default
```

Examples:

```text
Default
Profile 1
ContextVault
```

This setting is a profile directory name, not a filesystem path.

Absolute paths, `.`/`..`, slashes, backslashes, and null characters are rejected.

### CDP Endpoint

Default:

```text
http://127.0.0.1:9222
```

Used only by the explicit **Connect** workflow.

Most users should not change this setting.

### Start URL

Default:

```text
https://chatgpt.com/
```

The page opened when ContextVault launches the managed Chrome window.

## Export settings

### Default Folder

Default:

```text
exports
```

May be project-relative or absolute, provided the destination is writable.

### Archive Name

Default:

```text
{title}
```

Supported placeholders:

```text
{title}
{id}
{date}
```

Unsafe Windows filename characters are normalized.

When overwrite is off and a title already exists, ContextVault selects a stable identity-based suffix and then a numbered suffix if necessary.

### Auto Create Folder

Default: On

Creates the destination folder when allowed.

### Overwrite

Default: Off

When off, existing archives are preserved.

When on, a new archive is built and validated in staging before replacing the existing target.

### Compress

Default: Off

Enables compressed archive output in addition to the folder where supported.

### Verify Export

Default: On

Keep this enabled.

Verification checks structure, schemas, message order, references, asset integrity, hashes, counts, RAG consistency, and required files.

Disabling verification is not a recommended way to bypass an export error.

## Asset settings

### Images

Default: On

Extracts supported conversation images. Decorative favicon/interface images are filtered.

### Code

Default: On

Preserves code blocks and validates exact UTF-8 bytes.

### Tables

Default: On

Preserves structured table data.

### Attachments

Default: Off

Enables attachment retrieval. Private or expired attachments may be unavailable.

Attachment-specific UI fallback is used only for attachment resources.

### Markdown

Default: On

Produces readable conversation Markdown.

### JSON

Default: On

Produces machine-readable JSON documents.

### Summary

Default: On

Produces summary metadata.

### Statistics

Default: On

Produces conversation statistics.

### Search Index

Default: On

Produces a search index.

Core archive files and logs required by the format remain part of a valid archive.

## Performance settings

### Worker Threads

Default:

```text
4
```

Allowed values:

```text
1
2
4
8
```

This controls general background work. It does not create multiple simultaneous owners for the browser context.

### Message Retry Count

Default:

```text
5
```

Allowed range:

```text
1 to 20
```

This is the number of retries after the initial message capture attempt.

ContextVault retries the failed message/window, may perform one recovery reload while keeping verified checkpoints, and can preserve an exhausted message as a clearly marked degraded placeholder.

Infrastructure failures remain fatal.

### Delay Mode

Default:

```text
Normal
```

Allowed values:

```text
Auto
Fast
Normal
Safe
```

Delay Mode controls stabilization timing and image-render grace.

| Mode | Image-render grace | Use case |
|---|---:|---|
| Fast | 8 seconds | Fast systems and simple chats |
| Normal | 20 seconds | Recommended default |
| Safe | 45 seconds | Slow rendering or asset-heavy chats |
| Auto | 20 seconds | Automatic timing policy with normal image grace |

### Memory Mode

Default:

```text
Balanced
```

Allowed values:

```text
Low
Balanced
High
```

Memory Mode selects bounded internal readiness and resource policies. Use Balanced unless memory pressure or very large exports justify a different setting.

## Recommended profiles

### Normal user

```text
Worker Threads: 4
Message Retry Count: 5
Delay Mode: Normal
Memory Mode: Balanced
Verify Export: On
Attachments: Off
```

### Slow or image-heavy conversation

```text
Delay Mode: Safe
Message Retry Count: 5 to 10
Verify Export: On
```

### Low-memory system

```text
Worker Threads: 1 or 2
Memory Mode: Low
Delay Mode: Normal or Safe
```

## Editing settings manually

Manual editing is not recommended.

When necessary:

1. close ContextVault;
2. back up `data\settings.json`;
3. edit valid JSON only;
4. preserve property names and types;
5. restart and review the Logs page.

Invalid settings are recovered to defaults.
