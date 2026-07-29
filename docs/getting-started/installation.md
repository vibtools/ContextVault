# Installation

## Source installation

1. Install Python 3.12 or newer and Google Chrome Stable.
2. Create and activate a virtual environment.
3. Run `python -m pip install -r requirements.lock`.
4. Start with `python src/app.py` or `run.bat`.

Do **not** run `playwright install`; ContextVault uses the installed Google Chrome channel and does not bundle Chromium.

## Portable Windows release

Extract the entire `ContextVault-Windows-x64.zip` package and run `ContextVault.exe`. Keep the runtime directory beside the executable.

## First-run preparation

Leave **Browser Profile Root** blank and keep the profile name as `Default` unless a different ContextVault automation profile is needed. **Launch Chrome** creates and reuses `data/chrome-user-data`, opens a separate official Chrome window, and preserves the login performed inside that window.

Do not select Chrome's regular `...\Google\Chrome\User Data` directory for automation. If it is selected, ContextVault safely redirects Launch Chrome to its managed profile root instead of opening a blank tab in the already-running daily Chrome process.

Use **Connect** only when Chrome was intentionally started with remote debugging and a non-standard user-data directory.
