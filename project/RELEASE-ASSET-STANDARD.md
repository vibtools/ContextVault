# RELEASE-ASSET-STANDARD.md

# ContextVault Release Asset Standard

Version: 1.0

Applies To:

- GitHub Releases
- Release Packaging
- Build Pipeline
- Distribution Packages

Status:

ENGINEERING STANDARD

---

# Purpose

This document defines the official release asset standard for ContextVault.

It establishes the mandatory structure, naming conventions, packaging rules, validation requirements, and distribution standards for all release assets.

Every official release SHALL comply with this standard.

---

# Scope

This standard applies to:

- Stable Releases
- Beta Releases
- Release Candidates
- Hotfix Releases

---

# Objectives

Release assets SHALL be:

- Complete
- Portable
- Verified
- Consistent
- Versioned
- Reproducible

---

# Asset Categories

Every release SHALL include assets from the following categories:

- Executable
- Package
- Documentation
- Verification
- Metadata

---

# Mandatory Release Assets

Every official release SHALL contain:

- Windows x64 ZIP Package
- Standalone Executable
- README
- LICENSE
- CHANGELOG
- Release Notes
- SHA256 Checksums
- Build Information

GitHub Source Archives are supplemental and SHALL NOT replace executable release assets.

---

# Recommended Asset Structure

Release/

├── ContextVault-Windows-x64.zip
├── ContextVault.exe
├── README.txt
├── LICENSE
├── CHANGELOG.md
├── RELEASE-NOTES.md
├── SHA256SUMS.txt
└── BUILD-INFO.json

---

# Portable Package Structure

ContextVault/

├── ContextVault.exe
├── assets/
├── config/
├── docs/
├── LICENSE
└── README.txt

Only files required for runtime SHALL be included.

---

# Asset Naming Standard

Release asset names SHALL follow a consistent convention.

Examples:

ContextVault-Windows-x64.zip

ContextVault.exe

SHA256SUMS.txt

BUILD-INFO.json

README.txt

---

# Package Requirements

Every release package SHALL:

- extract successfully
- contain the executable
- contain required resources
- contain configuration
- contain documentation

Development-only files SHALL NOT be packaged.

---

# Documentation Assets

Every release SHALL include:

- README
- CHANGELOG
- LICENSE
- Release Notes

User-facing documentation SHALL match the released version.

---

# Verification Assets

Every release SHALL include:

- SHA256 checksums
- Build information

Future versions may include additional verification artifacts.

---

# Build Information

The release SHALL include build metadata.

Recommended information:

- Application Version
- Build Date
- Git Commit
- Git Tag
- Build Platform
- Python Version
- Nuitka Version

---

# Asset Validation

Every asset SHALL be validated before publication.

Verify:

✓ File exists

✓ File readable

✓ Correct filename

✓ Correct extension

✓ Expected size

✓ Successfully packaged

---

# Package Validation

Verify:

✓ ZIP opens correctly

✓ Files extract successfully

✓ Directory structure correct

✓ Executable present

✓ Resources present

✓ Documentation present

---

# Executable Validation

Verify:

✓ Executable exists

✓ Executable launches

✓ Required resources available

✓ Configuration accessible

---

# Documentation Validation

Verify:

✓ README included

✓ CHANGELOG included

✓ LICENSE included

✓ Release Notes included

---

# Integrity Validation

Verify:

✓ SHA256 generated

✓ Checksums match

✓ Package integrity confirmed

---

# Distribution Requirements

Release assets SHALL be suitable for:

- GitHub Releases
- Direct Download
- Offline Distribution
- Archive Storage

---

# Asset Retention

Published release assets SHALL remain available unless a release is formally withdrawn.

Replacement of release assets after publication is prohibited.

Corrections SHALL be published as a new release.

---

# Failure Policy

The release SHALL fail if:

- executable missing
- package missing
- checksum missing
- documentation missing
- validation failed

No incomplete release SHALL be published.

---

# Documentation Synchronization

Every release SHALL synchronize:

- README
- CHANGELOG
- Release Notes
- User Documentation
- Developer Documentation

Documentation SHALL reflect the published release.

---

# Related Standards

This standard SHALL be used together with:

- BUILD-SPECIFICATION.md
- NUITKA-BUILD-STANDARD.md
- GITHUB-ACTIONS-STANDARD.md
- GITHUB-RELEASE-STANDARD.md
- RELEASE-AUTOMATION-SPECIFICATION.md
- BUILD-VALIDATION-STANDARD.md

---

# AI Development Rules

Future AI implementations MUST NOT:

- publish source-only releases
- omit executable packages
- omit documentation
- omit integrity verification
- modify release assets without updating documentation
- publish incomplete release packages

---

# Acceptance Criteria

The Release Asset Package is considered compliant only if:

✓ Executable included

✓ Portable package generated

✓ Documentation included

✓ Checksums generated

✓ Build information included

✓ Validation completed

✓ Package verified

✓ Assets uploaded successfully

---

# Definition of Done

A release asset package is production-ready only when every required executable, package, document, verification file, and metadata file has been validated, packaged, and published according to the official ContextVault Release Asset Standard.

---

# Appendix A — Standard Release Asset Inventory

Every official release SHOULD include the following files:

Release/

├── ContextVault-Windows-x64.zip
├── ContextVault.exe
├── README.txt
├── LICENSE
├── CHANGELOG.md
├── RELEASE-NOTES.md
├── SHA256SUMS.txt
└── BUILD-INFO.json

---

# Appendix B — Release Asset Validation Checklist

| Asset                    | Required |
| ------------------------ | -------- |
| Windows Package          | ✓        |
| Executable               | ✓        |
| README                   | ✓        |
| LICENSE                  | ✓        |
| CHANGELOG                | ✓        |
| Release Notes            | ✓        |
| SHA256 Checksums         | ✓        |
| Build Information        | ✓        |
| ZIP Validation           | ✓        |
| Executable Validation    | ✓        |
| Documentation Validation | ✓        |
| Integrity Validation     | ✓        |

---

End of Document
