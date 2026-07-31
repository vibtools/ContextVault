# Troubleshooting

Use this guide for common problems in ContextVault 0.2.0.

## Start with these checks

1. Confirm the application version.
2. Confirm Windows 10/11 x64 and Google Chrome Stable.
3. Keep the complete portable folder together.
4. Use **Launch Chrome** for the normal workflow.
5. Leave Browser Profile Root blank.
6. Keep **Verify Export** enabled.
7. Reproduce once and review the Logs page.
8. Do not replace individual files inside a portable release.

## ContextVault does not start

### Portable release

- Extract the complete ZIP.
- Do not run from inside the ZIP.
- Keep runtime files beside `ContextVault.exe`.
- Move the folder to a writable location.
- Verify the release checksum.
- Review Windows security or antivirus notifications.

### Source

Run:

```powershell
python scripts/test/check_environment.py
python scripts/test/run_tests.py
python src/app.py
```

## Launch Chrome opens the wrong window or a blank tab

Use Browser Profile Root blank.

ContextVault should use:

```text
data\chrome-user-data
```

Do not select the regular Chrome `User Data` directory.

Close the separate ContextVault Chrome window if its profile is already in use, then launch again.

Do not delete Chrome singleton files or terminate unrelated daily Chrome processes.

## Managed profile is already in use

Close all Chrome windows launched by ContextVault.

Wait a few seconds and select **Launch Chrome** again.

If the application was forced closed, restart Windows only when the profile remains locked after normal Chrome shutdown.

## Connect reports connection refused

Example:

```text
ECONNREFUSED 127.0.0.1:9222
```

No Chrome instance is exposing the configured CDP endpoint.

Use **Launch Chrome** unless you intentionally started Chrome with remote debugging and a non-standard user-data root.

## ChatGPT login is missing

Log in manually inside the ContextVault Chrome window.

Do not enter credentials into ContextVault or copy cookies manually.

A session can expire because of ChatGPT or Chrome security policy.

## Scan finds no conversations

Check:

- ChatGPT is logged in;
- the sidebar is visible;
- the correct account or workspace is open;
- conversations have loaded;
- no modal is covering the page;
- the active URL is ChatGPT.

Refresh the ContextVault Chrome window and scan again.

A ChatGPT DOM change may require a new ContextVault release.

## Export does not start scrolling

Wait for the configured image-render grace if the conversation contains an unresolved image or spinner.

Normal mode can wait up to 20 seconds for the current image state before continuing.

Expected warning:

```text
image(s) ... did not finish browser rendering within 20.0s
```

After the warning, scrolling should continue if no other blocking condition remains.

Do not manually scroll during the test.

## Export remains on message stabilization

Review Logs for:

- blocking ChatGPT loader;
- active streaming;
- continue-generation control;
- zero-message shell;
- unresolved image grace;
- no-progress stall;
- checkpoint failure.

v0.2.0 separates image spinners from blocking loaders and uses semantic message stability. If the same state remains indefinitely without the expected warning, collect the complete log.

## Export takes longer than 900 seconds

v0.2.0 does not fail only because total runtime exceeds 900 seconds.

Meaningful progress allows the scan to continue.

A true no-progress stall can still fail.

Review whether message counts, checkpoint counts, or scroll position are changing.

## Export fails with no conversation messages

A real zero-message page is not accepted.

ContextVault performs one bounded recovery reload after an idle empty shell.

Check:

- the conversation still exists;
- access is allowed;
- ChatGPT finished loading;
- the URL is a conversation page;
- the account has permission;
- the DOM has not changed.

No empty partial archive is published.

## A browser image warning appears

The warning means an image or image placeholder did not finish browser rendering before the grace period.

ContextVault continued because stable message markup was checkpointed.

Actual asset retrieval and archive validation still decide whether the image is available.

Review:

```text
metadata.json
manifest.json
logs\export.log
logs\validation.log
```

## Export fails while collecting a favicon

Upgrade to v0.2.0 or later.

Decorative favicons are filtered and should not be routed through attachment fallback.

Do not disable archive verification to hide the error.

## Export tries to find an attachment control for an image

This is legacy behavior fixed in v0.2.0.

Install the complete current release. Do not replace only one Python file inside a portable build.

## One message repeatedly fails

Increase **Message Retry Count** only when needed.

ContextVault retries the message, can reload once, and preserves prior checkpoints.

After exhaustion, a safe degraded placeholder can be created.

Review:

```text
conversation.json → captureStatus, captureAttempts, captureError
metadata.json → captureWarnings
manifest.json → degraded/skipped counts
logs\export.log
```

A disk, browser, permission, or publication failure cannot be degraded safely.

## Export validation reports code mismatch

v0.2.0 compares exact UTF-8 bytes and preserves CRLF/LF.

Upgrade the complete application and export again.

Do not edit code files in the archive before validation.

## Export fails with FileExistsError

v0.2.0 resolves final names at publication time and prevents duplicate browser exports from interleaving.

Upgrade and retry.

When two conversations share a title, expect an identity suffix.

## Archive title is taken from an assistant heading

v0.2.0 uses the scanned sidebar conversation title.

Rescan the conversation list and export with the current version.

## Duplicate export is rejected

This is expected.

Only one complete browser workflow can own the browser context. Wait for the running export, cancel it safely, or let it finish before starting another operation.

## Long Windows path or temporary-file failure

v0.2.0 uses short same-directory temporary names.

Also:

- export to a reasonably short writable path;
- avoid deeply nested folders;
- avoid extremely long archive templates;
- check antivirus interference;
- verify available disk space.

## Export stops while loading assets

Private or expired assets may no longer be retrievable.

Retry while the authenticated conversation is open.

Enable attachments only when needed.

Review the exact resource kind and URL category in logs, but redact sensitive query strings before sharing.

## Validation reports a hash mismatch

Do not edit the archive in place.

Copy it again from the original destination or export again.

A hash mismatch means bytes differ from the manifest.

## Rebuild Summary does not repair the archive

Rebuild Summary is limited to summary regeneration and related manifest updates.

It does not repair missing messages, assets, or corrupted JSON.

## Cancellation shows an error traceback

Expected cancellation should be logged as:

```text
Browser command cancelled
Task cancelled
```

An ERROR traceback after cancellation can indicate an older `session_worker.py` or a different failure. Confirm the complete application version.

## Application says the export folder is inaccessible

- choose a folder your Windows account can write to;
- avoid protected system directories;
- ensure the drive is connected;
- check free space;
- close programs locking the destination;
- review antivirus or ransomware-protection rules.

## Settings reset to defaults

The previous settings file was invalid.

ContextVault preserves it with an invalid suffix and restores defaults.

Open Settings, review every value, and save again.

## Portable ZIP launches but resources are missing

Keep all distribution files together.

The extracted folder should include:

```text
ContextVault.exe
README.txt
LICENSE
data\
exports\
logs\
runtime\
```

Re-extract the verified ZIP.

## Locked module verification failed

This means the active Python interpreter does not match the exact versions in `requirements.lock`.

It does **not** mean the lock file is wrong, and it does not mean the 81-test suite failed.

Typical output looks like:

```text
FAIL beautifulsoup4: expected 4.13.5, installed 4.15.0
FAIL pydantic: expected 2.11.7, installed 2.10.6
```

Use the isolated release verifier instead of changing the project to match a shared Python installation:

```powershell
python scripts/release/verify_release_candidate.py --ref main --skip-chrome
```

To discard and recreate the isolated environment:

```powershell
python scripts/release/verify_release_candidate.py --ref main --skip-chrome --reset
```

The verifier creates `.venv-release`, installs exact locked dependencies there, and leaves the global Python environment unchanged.

Do not loosen pinned versions or edit `requirements.lock` only to match packages already installed on one computer.

## Test output contains `failed`, `error`, or a traceback but ends with `OK`

Several regression tests intentionally exercise failure handling. Expected examples include:

- rejecting a manifest with a missing hash;
- rejecting an altered asset or RAG count;
- rejecting broken message links or character counts;
- simulating an export exception to verify workflow-lock cleanup;
- preserving an exhausted message as a degraded placeholder.

These diagnostics are expected when the corresponding test ends with `ok` and the final suite summary is:

```text
Ran 81 tests

OK
```

A real test failure ends with `FAIL` or `ERROR`, produces a non-zero exit code, or does not finish with `OK`.

## Reporting a problem

Follow [SUPPORT.md](../../SUPPORT.md).

Never upload `data\chrome-user-data`.
