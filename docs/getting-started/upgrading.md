# Upgrading ContextVault

This guide covers a safe upgrade from v0.1.0 to v0.2.0 and the same general method for future portable releases.

## Why use a separate folder

A portable ContextVault folder contains both application files and personal runtime data. Extracting a new release directly over the only existing folder makes rollback and recovery harder.

The safest method is:

```text
old folder → backup personal data → extract new folder → test → restore selected data
```

## Personal data to preserve

Back up these paths when they exist:

```text
data\chrome-user-data\
data\settings.json
data\export_history.json
exports\
```

Optional:

```text
logs\
```

The checkpoint directory is temporary and should not normally be migrated:

```text
data\checkpoints\
```

Do not migrate old build outputs, partial files, invalid recovery files, or temporary files.

## Recommended upgrade steps

### 1. Finish or cancel active work

Do not upgrade during an export.

Close ContextVault and the separate Chrome window it launched.

### 2. Back up the old folder

Copy the entire old folder to a safe backup location, or at minimum copy the personal paths listed above.

### 3. Download and verify v0.2.0

Download the official ZIP and checksum from the release page.

Follow [Release verification](../guides/release-verification.md).

### 4. Extract to a new folder

Example:

```text
C:\Apps\ContextVault-0.2.0
```

### 5. First launch without copying data

Run the new version once to confirm that it opens.

Close it.

### 6. Restore selected personal data

Copy the old data into the matching paths in the new folder.

Recommended order:

1. `data\settings.json`
2. `data\export_history.json`
3. `exports\`
4. `data\chrome-user-data\` only after both applications and Chrome windows are closed

Do not merge a live Chrome profile while Chrome is running.

### 7. Start and verify

Open ContextVault 0.2.0.

Confirm:

- settings load;
- Launch Chrome opens the managed profile;
- ChatGPT login is present or can be restored by logging in again;
- Scan works;
- a small export completes and validates.

### 8. Keep rollback temporarily

Keep the old folder until the new version passes your normal workflow.

## Upgrade notes for v0.2.0

v0.2.0 changes export reliability, but does not intentionally change the frozen archive folder layout. Existing archives remain manageable.

The application version is `0.2.0`. The archive schema remains `1.0`.

## When settings recovery occurs

If `data\settings.json` is malformed or incompatible, ContextVault preserves the invalid file with an `.invalid`-style suffix and restores defaults.

Review settings after recovery.

## When login is missing

A copied Chrome profile can still require a new login because of Chrome, Windows, account security, profile-lock, or site-session behavior.

Log in manually in the ContextVault Chrome window. Do not copy cookies manually.

## Do not copy personal data into the public repository

Never copy these paths into a public Git working tree:

```text
data\chrome-user-data\
data\settings.json
data\export_history.json
data\checkpoints\
exports\
logs\
```
