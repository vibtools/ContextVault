# Quick Start

This guide is for people using the portable Windows release. No Python or development tools are required.

## Before you begin

You need:

- Windows 10 or Windows 11, 64-bit;
- Google Chrome Stable;
- a ChatGPT account;
- the extracted ContextVault release folder.

Do not run ContextVault from inside the downloaded ZIP.

## Step 1: Start ContextVault

Open the extracted folder and double-click:

```text
ContextVault.exe
```

The application opens in one main window with pages such as Dashboard, Conversations, Archives, Export History, Settings, Logs, and About.

## Step 2: Check Settings

Open **Settings**.

Use these recommended first-run values:

| Setting | Recommended value |
|---|---|
| Browser Profile Root | Leave blank |
| Profile | `Default` |
| CDP Endpoint | Leave the default |
| Default Folder | `exports` |
| Archive Name | `{title}` |
| Overwrite | Off |
| Compress | Your preference |
| Verify Export | On |
| Images | On |
| Code | On |
| Tables | On |
| Attachments | Off initially |
| Worker Threads | 4 |
| Message Retry Count | 5 |
| Delay Mode | Normal |
| Memory Mode | Balanced |

Save the settings.

## Step 3: Launch the managed Chrome window

Select **Launch Chrome**.

ContextVault opens a separate Google Chrome window using its managed profile:

```text
data\chrome-user-data
```

Log in to ChatGPT manually in that Chrome window.

Do not enter your ChatGPT password anywhere inside ContextVault.

Do not choose your normal Chrome `User Data` folder as Browser Profile Root.

## Step 4: Scan conversations

After ChatGPT has loaded:

1. Return to ContextVault.
2. Open **Conversations**.
3. Select **Scan**.
4. Wait for the conversation list.
5. Select the conversations you want.

A long list can take time to scan.

## Step 5: Export

Select **Export Selected** or **Export All**.

While export is active:

- keep the ContextVault Chrome window open;
- do not manually scroll the active conversation;
- do not start a second export;
- avoid navigating the Chrome tab away from ChatGPT.

ContextVault loads and checkpoints the conversation as it scrolls through virtualized history.

## Step 6: Understand warnings

A warning does not always mean the archive failed.

Examples:

- a browser image did not finish rendering before the grace period;
- one message was preserved as degraded after retries;
- an optional asset was unavailable.

Warnings are stored in the archive metadata and logs. Structural corruption or failed validation still prevents normal successful publication.

## Step 7: Open the archive

Open **Archives** and select the new archive.

You can:

- open its folder;
- open the readable Markdown file;
- validate it;
- rebuild its summary;
- delete it.

The easiest human-readable file is:

```text
conversation.md
```

The main machine-readable entry point is:

```text
manifest.json
```

## Where your files are stored

By default:

```text
exports\   Exported archives
logs\      Application logs
data\      Settings, history, checkpoints, and managed Chrome profile
```

Read [Privacy and local data](../security/privacy-and-local-data.md) before backing up or sharing the application folder.

## Next steps

- [Complete usage guide](../guides/usage.md)
- [Settings reference](../configuration/settings.md)
- [Troubleshooting](../troubleshooting/common-issues.md)
- [FAQ](../faq/index.md)
