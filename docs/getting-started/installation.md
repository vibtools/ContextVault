# Installation

ContextVault can be used as a portable Windows application or run from source.

## Portable Windows release

This is the recommended option for non-developers.

### Requirements

- Windows 10 or Windows 11, 64-bit
- Google Chrome Stable
- A ChatGPT account
- Disk space for the application, browser profile, and exports

### Download

From the GitHub Releases page, download:

```text
ContextVault-Windows-x64.zip
ContextVault-Windows-x64.zip.sha256
```

### Verify

Verify the ZIP before extraction. See [Release verification](../guides/release-verification.md).

### Extract

Extract the complete ZIP to a normal folder, for example:

```text
C:\Apps\ContextVault
```

Avoid:

- running directly from inside the ZIP;
- extracting into a temporary browser download view;
- moving only `ContextVault.exe`;
- placing the app in a folder that your account cannot write to.

### Run

Open the extracted folder and run:

```text
ContextVault.exe
```

Keep the entire distribution together.

## First-run Chrome profile

Leave **Browser Profile Root** blank unless you understand Chrome profile roots and intentionally maintain a separate non-standard profile.

With a blank setting, ContextVault uses:

```text
data\chrome-user-data
```

This creates a separate official Chrome window and preserves the ChatGPT login performed inside that window.

Do not choose Chrome's regular daily-browsing path, such as:

```text
%LOCALAPPDATA%\Google\Chrome\User Data
```

ContextVault does not safely automate a profile already owned by the normal Chrome process.

## Source installation

Source installation is intended for developers and advanced users.

### Requirements

- Windows 10 or Windows 11, 64-bit
- Python 3.12
- Git
- Google Chrome Stable

### Commands

```powershell
git clone https://github.com/vibtools/ContextVault.git
cd ContextVault

py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.lock

python scripts/test/check_environment.py
python scripts/test/run_tests.py
python src/app.py
```

You may also use:

```powershell
.\run.bat
```

after installing dependencies.

### Important Playwright note

Do not run:

```powershell
playwright install
```

ContextVault uses Google Chrome Stable installed on Windows and does not rely on a downloaded Playwright Chromium bundle.

## Installation data

The application creates local writable directories such as:

```text
data\
exports\
logs\
```

Do not install the portable build in a read-only location.

## Windows security prompts

Windows may display a reputation warning for a newly published unsigned open-source executable. Verify that:

- you downloaded the asset from the official repository release;
- the SHA-256 checksum matches;
- the ZIP name and release tag are correct.

Do not bypass security warnings for files downloaded from an untrusted mirror.

## Uninstall

ContextVault is portable. To uninstall:

1. close ContextVault and its managed Chrome window;
2. back up exports you want to keep;
3. delete the extracted application folder.

Deleting the folder also deletes the managed Chrome profile, settings, history, and logs stored inside it.

## Continue

- [Quick start](quick-start.md)
- [Upgrading](upgrading.md)
- [Usage guide](../guides/usage.md)
