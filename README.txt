ContextVault 0.2.0
==================

ContextVault saves fully loaded ChatGPT conversations as portable,
integrity-checked, RAG-ready archives.

SYSTEM REQUIREMENTS
-------------------
- Windows 10 or Windows 11, 64-bit
- Google Chrome Stable
- A ChatGPT account that you can log into manually
- Enough free disk space for exported conversations and assets

Python is not required for this portable release.

INSTALLATION
------------
1. Verify ContextVault-Windows-x64.zip with the accompanying
   ContextVault-Windows-x64.zip.sha256 file.
2. Extract the complete ZIP to a normal folder.
3. Do not run ContextVault directly from inside the ZIP.
4. Keep ContextVault.exe and all runtime files together.
5. Run ContextVault.exe.

FIRST USE
---------
1. Open Settings.
2. Leave Browser Profile Root blank.
3. Keep Profile set to Default.
4. Keep Verify Export enabled.
5. Select Launch Chrome.
6. Log in to ChatGPT manually inside the separate Chrome window.
7. Return to ContextVault and select Scan.
8. Select one or more conversations.
9. Select Export Selected or Export All.
10. Keep the ContextVault Chrome window open until export completes.

Most users should use Launch Chrome. Connect is only for an intentionally
remote-debugging-enabled Chrome instance.

LOCAL DATA
----------
ContextVault keeps local runtime data in the extracted application folder:

data\chrome-user-data\     Reusable authenticated Chrome profile
data\settings.json         Application settings
data\export_history.json   Export history
exports\                   Default export folder
logs\                      Application logs

The Chrome profile may contain cookies and authenticated session state.
Do not publish, commit, or share data\chrome-user-data.

UPGRADING
---------
Before replacing an older portable folder, back up:

data\chrome-user-data\
data\settings.json
data\export_history.json
exports\

Extract the new version into a separate folder, then copy back only the
personal runtime data you need.

IMPORTANT EXPORT NOTES
----------------------
- Large conversations may take time.
- Do not manually scroll the active conversation during export.
- ContextVault checkpoints messages before scrolling.
- A stalled browser image may produce a warning and the scan may continue.
- Keep Verify Export enabled.
- Do not replace individual files inside a portable build; install the
  complete updated release package.

RELEASE VERIFICATION
--------------------
PowerShell example:

$expected = ((Get-Content ".\ContextVault-Windows-x64.zip.sha256").Trim() -split "\s+")[0].ToLower()
$actual = (Get-FileHash ".\ContextVault-Windows-x64.zip" -Algorithm SHA256).Hash.ToLower()
if ($actual -ne $expected) { throw "Checksum verification failed." }
"Checksum verified: $actual"

DOCUMENTATION
-------------
https://github.com/vibtools/ContextVault

Support:
https://github.com/vibtools/ContextVault/blob/main/SUPPORT.md

Security:
https://github.com/vibtools/ContextVault/blob/main/SECURITY.md

LICENSE
-------
MIT License. See LICENSE in this folder.
