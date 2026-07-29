# 📜 Changelog

All notable changes to **ContextVault** will be documented in this file.

The format of this changelog is based on the principles of **Keep a Changelog**, and the project follows **Semantic Versioning (SemVer)**.

* Changelog Format: https://keepachangelog.com/
* Semantic Versioning: https://semver.org/

---

# Versioning Policy

ContextVault uses Semantic Versioning:

```text
MAJOR.MINOR.PATCH
```

* **MAJOR** – Breaking changes or incompatible architecture changes.
* **MINOR** – New features that remain backward compatible.
* **PATCH** – Bug fixes, performance improvements, documentation updates, and non-breaking maintenance.

---

# Release Types

| Release Type           | Description                                 |
| ---------------------- | ------------------------------------------- |
| Alpha                  | Early internal development                  |
| Beta                   | Feature-complete but still under testing    |
| RC (Release Candidate) | Candidate for the next stable release       |
| Stable                 | Official production release                 |
| Hotfix                 | Critical fix for an existing stable release |

---

# [Unreleased]

## Added

* Upcoming features under active development.

## Changed

* Improvements not yet released.

## Fixed

* Bug fixes awaiting release.

## Removed

* Features scheduled for removal before release.

## Security

* Security improvements awaiting release.

---

# [1.0.0] - Initial Release

## Added

* Initial ContextVault architecture.
* CustomTkinter desktop interface.
* Playwright automation engine.
* Google Chrome integration.
* Archive generation pipeline.
* Portable OneDir runtime.
* GitHub Actions build pipeline.
* Structured project documentation.
* AI development workflow.
* JSON schema support.
* Project manifest (`vibproject.ygit`).

## Changed

* Initial production-ready architecture.

## Fixed

* Initial release.

## Security

* Initial security policy implemented.

---

# Changelog Categories

Every release should use the following categories when applicable.

## Added

New functionality.

Examples:

* New features
* New modules
* New commands
* New integrations

---

## Changed

Existing behavior that has been modified.

Examples:

* Performance improvements
* UI improvements
* Workflow improvements
* Refactoring
* Architecture improvements (only when officially approved)

---

## Deprecated

Features that remain available but are scheduled for removal.

Every deprecated feature should indicate:

* When it became deprecated.
* The recommended replacement.
* The planned removal version.

---

## Removed

Features permanently removed.

Document:

* What was removed.
* Why it was removed.
* Replacement (if applicable).

---

## Fixed

Bug fixes.

Examples:

* Crash fixes
* Parsing fixes
* Browser fixes
* Build fixes
* Export fixes

---

## Security

Security-related changes.

Examples:

* Vulnerability fixes
* Dependency updates
* Hardening
* Permission improvements
* Validation improvements

---

# Changelog Rules

Every release entry should:

* Include the released version.
* Include the release date.
* Describe only user-visible or developer-relevant changes.
* Be written in clear language.
* Group changes under the correct section.
* Avoid duplicate entries.

---

# Version Number Guidelines

Increase versions according to impact.

## Patch

Examples:

```text
1.0.0 → 1.0.1
```

Use for:

* Bug fixes
* Documentation updates
* Performance optimizations
* Internal refactoring
* Build improvements

---

## Minor

Examples:

```text
1.0.0 → 1.1.0
```

Use for:

* New features
* New export options
* New parsers
* New supported formats

without breaking compatibility.

---

## Major

Examples:

```text
1.0.0 → 2.0.0
```

Use only for:

* Breaking API changes
* Breaking archive format changes
* Breaking project architecture
* Incompatible runtime changes

Major releases require updated project documentation and migration guidance.

---

# Release Checklist

Before adding a new release to this changelog, verify:

* Version number updated.
* Release completed successfully.
* GitHub Actions passed.
* Documentation updated.
* Release notes finalized.
* No unresolved release-blocking issues.

---

# Writing Guidelines

Write entries that answer:

* What changed?
* Why was it changed?
* Does it affect users?
* Does it require action?

Keep entries concise and factual.

Avoid marketing language.

---

# Historical Integrity

Once a version has been officially released:

* Do not rewrite its history.
* Do not silently modify entries.
* Corrections should be recorded in a later release.

The changelog is a historical record of the project.

---

# Final Standard

Every official release of ContextVault must include a corresponding changelog entry.

The changelog should accurately document the project's evolution and provide a reliable history for users, contributors, maintainers, and future developers.
