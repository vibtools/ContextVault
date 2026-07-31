# Privacy and Local Data

ContextVault works with potentially private ChatGPT conversations and an authenticated Chrome profile. This page explains what is stored and how to protect it.

## Local-first storage

ContextVault writes application data to the local filesystem.

It does not provide built-in cloud synchronization or a hosted archive account.

ChatGPT is accessed through the normal authenticated website in Google Chrome.

## Managed Chrome profile

Default location:

```text
data\chrome-user-data\
```

This profile may contain:

- ChatGPT cookies;
- authenticated session state;
- Chrome preferences;
- cache and site data;
- browsing state created in the managed profile.

It is not merely a configuration folder.

### Protect it

- Do not commit it to Git.
- Do not upload it to an issue.
- Do not include it in a public project ZIP.
- Do not share it with another person.
- Do not copy it while the managed Chrome window is running.
- Protect the Windows account and storage device.

Deleting the profile signs the managed browser out and removes its local profile state.

## Settings

Location:

```text
data\settings.json
```

Settings can include local export paths, profile root, profile name, CDP endpoint, archive naming, enabled assets, and performance preferences.

Settings should not contain ChatGPT credentials, but local paths can still reveal personal information.

## Export history

Location:

```text
data\export_history.json
```

History can include conversation titles, status, timestamps, and archive paths.

## Checkpoints

Location:

```text
data\checkpoints\
```

Checkpoints are temporary verified message data used during an active export.

ContextVault removes them after success, cancellation, or failure cleanup. A process crash can leave remnants that should be treated as private conversation data.

## Exports

Default location:

```text
exports\
```

Archives can contain the complete conversation and assets.

They may include personal text, code, images, uploaded files, citations, titles, URLs, timestamps, generated summaries, and keywords.

Use encryption, access controls, and backups appropriate to the content.

## Logs

Location:

```text
logs\
```

Logs are intended for diagnostics. They can include conversation titles, ChatGPT URLs, local paths, resource URLs, error messages, and operation timing.

Logs must not intentionally contain passwords or session cookies, but always review and redact before sharing.

## Backups

Recommended backup targets:

```text
exports\
data\settings.json
data\export_history.json
```

Back up `data\chrome-user-data` only when you understand the sensitivity and both ContextVault and Chrome are closed.

Encrypt backups that contain private conversations or authenticated browser state.

## Public repository boundary

Never copy these runtime paths into the public repository:

```text
data\chrome-user-data\
data\settings.json
data\export_history.json
data\checkpoints\
exports\
logs\
```

The public repository should contain only source, tests, configuration defaults and schemas, assets, templates, and public documentation.

## Sharing a support package

Share the minimum evidence.

Good:

- exact error;
- small redacted log section;
- application version;
- Windows and Chrome versions;
- reproducible steps.

Avoid:

- complete profile;
- complete archive;
- cookies;
- authorization headers;
- account email;
- private conversation text;
- sensitive local paths.

## Deleting data

To remove one archive, use the Archives page or delete the intended archive folder after closing ContextVault.

To reset the managed browser session, close ContextVault and Chrome, then delete:

```text
data\chrome-user-data\
```

To fully remove the portable application, back up needed exports and delete the extracted application folder.

## Security incidents

If local session data was exposed:

1. stop sharing the affected file;
2. sign out of ChatGPT sessions;
3. change relevant account credentials when appropriate;
4. remove the exposed Chrome profile copy;
5. review account security;
6. report a ContextVault vulnerability privately when application behavior caused the exposure.

See [SECURITY.md](../../SECURITY.md).
