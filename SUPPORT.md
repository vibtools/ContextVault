# ContextVault Support

This page explains where to start when ContextVault does not behave as expected.

## Before asking for help

1. Confirm that you are using the latest official release.
2. Read:
   - [Quick start](docs/getting-started/quick-start.md)
   - [Common issues](docs/troubleshooting/common-issues.md)
   - [FAQ](docs/faq/index.md)
   - [Known limitations](docs/guides/known-limitations.md)
3. Restart ContextVault and its separate Chrome window.
4. Reproduce the problem once.
5. Collect the relevant application log and exact error text.
6. Remove personal or sensitive information before sharing.

## Public bug reports

Use a public GitHub issue for ordinary bugs.

Include:

- ContextVault version;
- Windows version;
- Google Chrome version;
- source or portable release;
- exact steps;
- expected result;
- actual result;
- relevant log excerpt;
- whether the problem occurs in one conversation or all conversations;
- approximate message count and asset types;
- whether the export completed with warnings or failed.

Do not upload the complete `data\chrome-user-data` folder.

## User questions

For usage questions, clearly describe the screen and button you are using. Screenshots are helpful after personal information is removed.

## Security issues

Do not use a public issue for a security vulnerability. Follow [SECURITY.md](SECURITY.md).

## Sensitive logs and archives

Logs and exported archives may contain conversation titles, ChatGPT URLs, local filesystem paths, timestamps, personal conversation content, and asset filenames.

Share the smallest redacted excerpt that demonstrates the problem.

## Unsupported environments

The official release targets Windows 10 or Windows 11, 64-bit; Google Chrome Stable; and the ContextVault-managed profile or an explicitly configured non-standard profile.

Other operating systems, browsers, modified Chromium builds, corporate browser policies, and unsupported ChatGPT interfaces may not work.

## Build problems

For a source or Nuitka build problem, include:

```powershell
python --version
python scripts/test/check_environment.py --skip-chrome
python scripts/test/run_tests.py
git rev-parse HEAD
```

Include the failing step and the first actionable error, not only the final exit code.
