# Frequently Asked Questions

## Do I need to know programming?

No. Use the portable Windows release, extract it, and run `ContextVault.exe`.

## Do I need Python?

Not for the portable release. Python 3.12 is required only when running from source.

## Which operating systems are supported?

Windows 10 and Windows 11, 64-bit.

## Which browser is supported?

Google Chrome Stable.

## Does ContextVault ask for my ChatGPT password?

No. You log in manually inside the Chrome window opened by ContextVault.

## Where is the Chrome login stored?

By default, in the local managed profile:

```text
data\chrome-user-data
```

Treat this folder as sensitive.

## Can I use my normal Chrome profile?

Do not use the normal daily Chrome `User Data` root.

Leave Browser Profile Root blank so ContextVault uses its own managed profile.

## What is Connect?

Connect attaches to an intentionally remote-debugging-enabled Chrome instance.

It is an advanced option. Most users should choose Launch Chrome.

## Does ContextVault upload my conversations?

ContextVault creates local archives. It does not provide built-in cloud synchronization.

ChatGPT itself is accessed through the normal authenticated web interface in Chrome.

## Where are exports stored?

The default is:

```text
exports
```

You can change the destination in Settings.

## What does Verify Export do?

It checks required files, schemas, message order, references, assets, hashes, sizes, counts, and RAG consistency.

Keep it enabled.

## Why can a large export take a long time?

ContextVault loads virtualized history, waits for stable messages, checkpoints content, downloads assets, builds indexes, and validates the result.

A large conversation may contain hundreds of messages and many assets.

## Is there still a 900-second total limit?

v0.2.0 continues beyond a fixed wall-clock duration while meaningful progress occurs.

A true no-progress stall can still fail.

## What is a checkpoint?

A checkpoint is a temporary verified copy of a message window saved before the browser scrolls away.

It is not part of the final archive and is cleaned after the operation.

## What is a degraded message?

A message that could not be fully verified after configured retries can be preserved with visible fallback content and an explicit warning.

It is not silently omitted.

## Why did I receive an image warning?

An image or spinner did not finish browser rendering before the configured grace period.

ContextVault continued the scan and kept the warning. Asset download and final validation remain authoritative.

## What are the image grace periods?

```text
Fast    8 seconds
Normal 20 seconds
Safe   45 seconds
Auto   20 seconds
```

## Are attachments included?

Attachments are disabled by default. Enable them in Settings when required.

Some private or expired attachments may be unavailable.

## Why was a second export rejected?

ContextVault allows one complete browser workflow at a time to prevent conversation switching, message-count corruption, and archive races.

## Why does an archive name contain an ID suffix?

Two conversations can share the same visible title.

ContextVault adds a stable identity suffix to preserve both archives when overwrite is off.

## Can I edit an archive?

You can, but manual edits can invalidate hashes and references.

Keep an original validated copy.

## What is the easiest file to read?

```text
conversation.md
```

## What is the machine-readable entry point?

```text
manifest.json
```

## What does RAG-ready mean?

The archive includes structured documents and chunks that an external retrieval system can consume.

ContextVault does not include a vector database or embedding model.

## Can ContextVault reopen an archive as a chat?

The application manages and validates archives but does not currently provide an in-app chat-with-archive system.

## How do I update?

Extract the new version into a separate folder and preserve your personal runtime data. Read [Upgrading](../getting-started/upgrading.md).

## How do I verify the download?

Use the `.sha256` file. Read [Release verification](../guides/release-verification.md).

## How do I report a bug?

Read [SUPPORT.md](../../SUPPORT.md).

## How do I report a security issue?

Read [SECURITY.md](../../SECURITY.md). Do not disclose vulnerability details publicly.

## What is the difference between version 0.2.0 and schema 1.0?

`0.2.0` is the application release.

`1.0` is the archive data-format schema.

A bug-fix release does not require an archive schema change when the format remains compatible.
