# Troubleshooting

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
