# Troubleshooting

## Export fails with `Code reference ... file content does not match rawCode`

Older validation read code files as text, allowing Windows universal-newline conversion to change `\r\n` into `\n` before comparison. The file bytes and `rawCode` could therefore be identical in meaning but falsely fail validation. The corrected validator compares exact UTF-8 bytes and the archive builder immediately reads back every code file. Install the current source files and export again; do not disable export verification to hide this error.

## One message repeatedly fails during a large conversation

Set **Message Retry Count** in Settings. ContextVault retries only the failed message/window, reloads the page once while preserving completed checkpoints, and resumes scanning. When retries are exhausted, it keeps an explicit degraded placeholder and continues instead of discarding the entire conversation. Review `metadata.json` → `captureWarnings`, `manifest.json` → `skippedMessages`, `conversation.json` → message `captureStatus`, and `logs/export.log`.

If the application still aborts, the failure is not a skippable message-content mismatch. Check for browser termination, a full/inaccessible disk, export-folder permissions, malformed settings, or an inability to persist the degraded placeholder itself.

## Export fails with “No conversation messages were found” while ChatGPT is still loading

This error identifies the legacy count-only loader. That loader could treat four unchanged zero-message polls as completion when the current ChatGPT spinner did not match its old loading selector. Install the corrected browser readiness files, restart ContextVault, rescan, and export again. The corrected loader never reports readiness with zero messages; it waits for delayed React rendering, visible loading indicators, streaming completion, message stabilization, and virtualized-history scanning. A genuine timeout is reported as a readiness error and no partial archive is written.

## Launch Chrome opens a blank tab in normal Chrome

This indicates that an older build attempted to automate Chrome's regular `User Data` directory. Chrome's process-singleton redirected `about:blank` to the already-running daily browser and terminated the attempted automation process. Replace `src/browser/browser_manager.py` with the corrected version. The corrected Launch Chrome path uses `data/chrome-user-data` and does not attach to the regular Chrome session.

## ContextVault automation profile is already in use

Close the separate Chrome window previously launched by ContextVault, then select **Launch Chrome** again. Do not delete Chrome singleton files or force-terminate unrelated daily Chrome processes.

## Connect reports `ECONNREFUSED 127.0.0.1:9222`

No Chrome process is exposing the configured CDP endpoint. **Connect** is only for a browser intentionally started with remote debugging and a non-standard user-data directory. Use **Launch Chrome** for the normal ContextVault workflow.

## No conversations found

Confirm ChatGPT is logged in inside the ContextVault Chrome window, the sidebar is visible, and conversations have loaded. Refresh Chrome and scan again. ChatGPT DOM changes may require selector maintenance.

## Export stops while loading assets

Review the Logs page and archive export log. Private or expired resources may no longer be retrievable. Retry while the authenticated conversation remains open.

## Validation reports a missing asset or hash mismatch

Do not edit an archive in place. Export again, or use Rebuild Summary only for summary regeneration; that operation updates manifest integrity metadata.

## Application does not start

From source, run `python scripts/test/check_environment.py`. For a portable build, extract the complete ZIP and keep all runtime files beside `ContextVault.exe`.
