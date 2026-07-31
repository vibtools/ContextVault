# Usage Guide

1. Open ContextVault.
2. Configure the profile name and export settings. Leave Browser Profile Root blank for the ContextVault-managed persistent profile.
3. Set **Message Retry Count** in Settings. The default is 5 retries after the initial message capture attempt.
4. Choose **Launch Chrome**. Choose **Connect** only for an intentionally CDP-enabled Chrome instance using a non-standard user-data directory.
5. Log in to ChatGPT manually inside the ContextVault Chrome window when needed. ContextVault never requests or stores a password.
6. Open the target conversation or use **Scan** to load sidebar conversations.
7. Select one or more conversations.
8. Choose **Export Selected** or **Export All**.
9. Monitor progress, logs, and notifications. During large exports, ContextVault verifies each stabilized message window before scrolling away from it.
10. Open **Archives** to view Markdown, open folders, validate, rebuild summaries, or delete an archive.

Exports are sequential at the browser boundary so the persistent Playwright context remains thread-safe. Asset processing and non-browser tasks use the managed worker pool. Cancellation is cooperative; Resume is available only for the interrupted queue in the current application session.

## Recovery behavior

A failed message does not restart the entire conversation immediately. ContextVault retries that specific message while keeping the current window stable. If required, it reloads the page once, retains already verified checkpoints, and resumes the upward scan. After all configured retries are exhausted, the message's visible text, order, role, source key, capture time, attempt count, and failure reason are retained as a degraded placeholder. The export notification, metadata, manifest, Markdown, export log, and validation log identify the degraded count.

Do not close the ContextVault Chrome window while export is active. A browser termination, full disk, permission failure, or inability to write a valid archive cannot be safely skipped and remains fatal.
