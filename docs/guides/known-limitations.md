# Known Limitations

ContextVault is designed for a specific supported environment. Understanding these limitations helps distinguish a product limitation from a defect.

## Platform

The official application targets Windows 10 and Windows 11, 64-bit.

Linux, macOS, Windows on ARM, Wine, and remote application virtualization are not official release targets.

## Browser

Google Chrome Stable is the supported browser.

ContextVault does not officially support Microsoft Edge, Firefox, Brave, portable Chromium builds, a Playwright-downloaded Chromium bundle, or a normal daily Chrome profile already owned by another Chrome process.

## ChatGPT interface changes

ContextVault observes the current ChatGPT web interface. ChatGPT can change its DOM, loading indicators, message containers, sidebar, asset controls, and virtualization behavior without notice.

Selector maintenance may be required after a major interface change.

ContextVault reports unsupported states rather than inventing content.

## Authentication

ContextVault does not automate login credentials.

You must log in manually. Account security controls, multi-factor authentication, organization policies, session expiration, and geographic restrictions remain controlled by ChatGPT and Chrome.

## Assets

Images and attachments can be private, expired, generated dynamically, stored behind authenticated URLs, or represented by temporary blob/data resources.

An archive can complete with explicit asset warnings when optional content is unavailable. Mandatory structural validation still applies.

Attachments are disabled by default.

## Large conversations

Large conversations can take a long time because ContextVault must load virtualized history, wait for stable message windows, checkpoint messages, download assets, generate indexes and RAG files, and validate the archive.

Meaningful progress can exceed the configured stall duration. A long runtime alone is not a failure.

## Browser-rendered images

An image placeholder can remain unresolved in the browser even when message markup is otherwise stable.

ContextVault applies a bounded grace period and may continue with a warning. This avoids a permanent scroll deadlock but does not guarantee that every remote image is available for download.

## Timestamps

ChatGPT does not always expose a reliable timestamp for every message.

When no trustworthy source timestamp is available, the message timestamp can be `null`, capture time is stored separately, and conversation start/end times are not invented.

## Degraded messages

After configured retries, one message can be preserved as an explicit degraded placeholder.

This protects message order and makes the limitation visible. It is not equivalent to a fully verified message.

Review capture warnings before using the archive for legal, compliance, scientific, or evidentiary purposes.

## No cloud synchronization

ContextVault writes local archives. It does not provide built-in cloud synchronization, team sharing, remote backup, or account-based archive storage.

Use your own secure backup process.

## No semantic search service

RAG-ready JSON files are generated, but ContextVault does not bundle an embedding model, vector database, hosted retrieval service, or chat-with-archive interface.

## Archive editing

Manual edits can invalidate hashes, references, counts, and RAG consistency.

Use ContextVault's validation and summary rebuild functions where applicable. Do not assume an edited archive remains valid.

## Portable application trust

The release workflow produces a ZIP and SHA-256 file. Code signing may not be available for every open-source release, so Windows reputation warnings can occur.

Always verify the official checksum.

## Performance

Performance depends on conversation length, number and size of assets, ChatGPT response speed, Chrome behavior, disk speed, antivirus scanning, available memory, and delay/memory settings.

Increasing worker threads does not make the single browser context parallel.

## Privacy

The managed Chrome profile and exported conversations are local but sensitive. ContextVault does not make the device itself secure.

Use Windows account security, disk encryption, backups, and access controls appropriate to your data.
