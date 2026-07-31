# ContextVault Security Policy

ContextVault processes authenticated browser sessions and potentially private conversation content. Security reports are treated seriously.

## Supported versions

| Version | Support |
|---|---|
| 0.2.x | Full support |
| 0.1.x | Critical security fixes when practical |
| Development branch | No stability guarantee |
| Older or unofficial builds | Unsupported |

## Reporting a vulnerability

Do **not** publish vulnerability details in a public GitHub issue, discussion, pull request, log, or screenshot.

Preferred reporting path:

1. Open the repository's **Security** tab.
2. Select **Advisories** or **Report a vulnerability** when GitHub private vulnerability reporting is available.
3. Submit the report privately.

When the private-reporting option is not visible, contact the repository maintainers through the repository owner's public contact channel and request a private security contact. Do not include exploit details in that initial public message.

A useful report includes:

- affected ContextVault version;
- Windows version;
- clear impact;
- reproduction steps;
- proof of concept, when safe;
- affected files or components;
- whether authenticated browser data or exported content is exposed;
- suggested mitigation, when known.

## Expected handling

Maintainers aim to acknowledge the report, reproduce and assess severity, limit further exposure, prepare and test a fix, publish a corrected release, and coordinate disclosure when appropriate.

Response time depends on severity and maintainer availability. Do not assume a report is accepted until it is confirmed.

## Security scope

Relevant reports include:

- arbitrary file read or write;
- path traversal;
- archive extraction or publication outside the selected root;
- command injection;
- unsafe subprocess construction;
- credential, cookie, token, or session exposure;
- unauthorized access to `data\chrome-user-data`;
- insecure temporary files;
- unsafe archive deletion;
- validation bypass;
- corrupted archive accepted as valid;
- dependency or build-pipeline compromise;
- browser automation that weakens Chrome security;
- sensitive information written to public logs;
- malicious content causing code execution.

## Usually not a security vulnerability

The following are generally handled as normal bugs unless they create a security impact:

- cosmetic UI defects;
- ordinary export failures;
- unsupported ChatGPT DOM changes;
- spelling or documentation mistakes;
- slow exports;
- missing assets that are clearly reported;
- user deletion of their own archive;
- unsupported operating systems or browsers.

## Local data security

ContextVault stores runtime data locally.

### Chrome profile

```text
data\chrome-user-data\
```

This directory may contain cookies, authenticated session state, Chrome profile preferences, site data, and browser cache.

Treat it as sensitive. Do not commit it to Git, upload it to an issue, include it in a public ZIP, copy it to an untrusted device, or share it with another person.

Anyone who can access the profile and device may be able to use its authenticated sessions.

### Settings, history, exports, and logs

```text
data\settings.json
data\export_history.json
exports\
logs\
```

These paths can reveal local directories, conversation titles, URLs, timestamps, exported content, and diagnostic information.

Review and redact before sharing.

## Credential handling

ContextVault does not request a ChatGPT password. Authentication is performed manually in Google Chrome.

No contributor may add password collection, token scraping, cookie export, hidden credential transmission, hardcoded secrets, or telemetry that exposes conversation content without an explicit approved design and disclosure.

## Browser security

ContextVault must:

- use Google Chrome Stable as documented;
- use a separate managed profile by default;
- avoid automating the user's regular daily Chrome `User Data` root;
- keep Playwright objects on the dedicated browser worker;
- avoid disabling browser security controls without explicit justification;
- close browser resources predictably;
- avoid automatic attachment-style interaction for unrelated image resources.

## Filesystem and archive security

The application must preserve:

- root containment checks;
- Windows-safe filename normalization;
- archive-relative path validation;
- path traversal rejection;
- direct-child archive deletion restrictions;
- atomic staging and publication;
- short same-directory temporary files;
- SHA-256 verification;
- explicit warnings and failures.

Do not weaken validation to make a failing export appear successful.

## Dependency and build security

Release builds must use locked dependencies and a clean Windows runner or a verified local environment.

Before release:

- install from `requirements.lock` and `requirements-build.lock`;
- run the forensic tests;
- build with the official Nuitka configuration;
- verify the packaged ZIP;
- publish the SHA-256 checksum;
- review workflow logs;
- avoid untrusted release assets.

## Log sharing checklist

Before attaching a log:

- remove cookies, tokens, and authorization headers;
- remove personal conversation text;
- remove private file paths where unnecessary;
- remove email addresses and account identifiers;
- keep the error, timestamp, operation, and relevant stack trace;
- state the application version and Windows version.

## Disclosure credit

Maintainers may credit reporters with permission. Anonymous reporting is respected when the reporting channel supports it.

## Privacy guidance

Read [Privacy and local data](docs/security/privacy-and-local-data.md) for user-facing retention and backup guidance.
