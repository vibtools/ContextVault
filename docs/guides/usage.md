# Usage Guide

1. Open ContextVault.
2. Configure the profile name and export settings. Leave Browser Profile Root blank for the ContextVault-managed persistent profile.
3. Choose **Launch Chrome**. Choose **Connect** only for an intentionally CDP-enabled Chrome instance using a non-standard user-data directory.
4. Log in to ChatGPT manually inside the ContextVault Chrome window when needed. ContextVault never requests or stores a password.
5. Open the target conversation or use **Scan** to load sidebar conversations.
6. Select one or more conversations.
7. Choose **Export Selected** or **Export All**.
8. Monitor progress, logs, and notifications.
9. Open **Archives** to view Markdown, open folders, validate, rebuild summaries, or delete an archive.

Exports are sequential at the browser boundary so the persistent Playwright context remains thread-safe. Asset processing and non-browser tasks use the managed worker pool. Cancellation is cooperative; Resume is available only for the interrupted queue in the current application session.
