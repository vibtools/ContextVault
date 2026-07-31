# Public Documentation Package Scope

This documentation set is prepared for the ContextVault v0.2.0 public release.

## Goals

- make the portable application usable by non-developers;
- remove public dependencies on unavailable private documents;
- correct the 0.1.0 and 0.2.0 application version history;
- keep archive schema 1.0 distinct from application version 0.2.0;
- document verified export reliability fixes;
- provide upgrade, checksum, privacy, support, security, limitations, and release guidance;
- avoid claims not supported by source or CI evidence.

## Included root documents

```text
README.md
README.txt
CHANGELOG.md
PROJECT_STRUCTURE.md
CONTRIBUTING.md
SECURITY.md
CODE_OF_CONDUCT.md
SUPPORT.md
.github/PULL_REQUEST_TEMPLATE.md
```

## Included documentation categories

```text
docs/api/
docs/configuration/
docs/developer/
docs/faq/
docs/features/
docs/getting-started/
docs/guides/
docs/release-notes/
docs/security/
docs/troubleshooting/
```

## Not included

This package intentionally does not modify Python source, tests, workflow YAML, build configuration, dependency locks, JSON schemas, icons, images, runtime data, Chrome profiles, exports, logs, or personal maintainer documents.

Version metadata outside documentation must be synchronized separately before the v0.2.0 tag is pushed.
