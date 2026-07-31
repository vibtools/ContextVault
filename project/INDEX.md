# 📑 ContextVault Engineering Documentation Index

This document is the master index for all engineering documentation contained in the `project/` directory.

It serves as the official navigation guide for contributors, maintainers, reviewers, QA engineers, release managers, and AI-assisted development systems.

All engineering decisions, implementation work, testing, validation, and releases SHALL follow the specifications referenced by this document.

---

# Project Information

| Property              | Value                      |
| --------------------- | -------------------------- |
| Project               | ContextVault               |
| Directory             | `/project`                 |
| Documentation Type    | Engineering Specifications |
| Status                | Active                     |
| Maintainer            | Vib Tools                  |
| Documentation Version | 2.0                        |

---

# Purpose

The documents in this directory define the official engineering rules for ContextVault.

These specifications establish:

- Project architecture
- Product functionality
- Technology stack
- Engineering standards
- Export engine behavior
- Build system
- Release process
- Testing requirements
- Versioning policy
- Documentation policy
- AI development rules

This directory is the authoritative engineering reference for the project.

---

# Documentation Reading Order

New contributors and AI systems SHOULD read the documents in the following order.

---

# Phase 1 — Project Foundation

| Order | Document                    | Purpose                                      |
| ----: | --------------------------- | -------------------------------------------- |
|     1 | PROJECT-OVERVIEW.md         | Project vision, goals, philosophy and scope  |
|     2 | PROJECT-ARCHITECTURE.md     | Overall system architecture                  |
|     3 | PROJECT-CODING-STANDARDS.md | Coding conventions and engineering practices |

---

# Phase 2 — Product Definition

| Order | Document                               | Purpose                        |
| ----: | -------------------------------------- | ------------------------------ |
|     4 | FEATURE-FREEZE-SPECIFICATION.md        | Official feature specification |
|     5 | CONTEXTVAULT-UI-FEATURE-FREEZE.md      | User interface specification   |
|     6 | ARCHIVE-FORMAT-FREEZE-SPECIFICATION.md | Archive format specification   |

---

# Phase 3 — Technology Freeze

| Order | Document                                                 | Purpose                           |
| ----: | -------------------------------------------------------- | --------------------------------- |
|     7 | CONTEXTVAULT-OFFICIAL-UI-TECHNOLOGY-FREEZE.md            | Approved UI technologies          |
|     8 | CONTEXTVAULT-BROWSER-AUTOMATION-TECHNOLOGY-FREEZE.md     | Browser automation stack          |
|     9 | CONTEXTVAULT-OFFICIAL-MODULES-AND-DEPENDENCIES-FREEZE.md | Official modules and dependencies |
|    10 | CONTEXTVAULT-BUILD-AND-RELEASE-PIPELINE-FREEZE.md        | Approved build pipeline           |
|    11 | DEPENDENCY-INTEGRITY-AND-BUILD-RELIABILITY-POLICY.md     | Dependency and build reliability  |

---

# Phase 4 — Export Engine

| Order | Document                            | Purpose                            |
| ----: | ----------------------------------- | ---------------------------------- |
|    12 | BUGFIX-v0.2.0.md                    | Export reliability objectives      |
|    13 | EXPORT-ENGINE-SPECIFICATION.md      | Export engine architecture         |
|    14 | CHATGPT-COMPATIBILITY-STANDARD.md   | ChatGPT compatibility requirements |
|    15 | CHATGPT-DOM-OBSERVATION-STANDARD.md | DOM observation rules              |
|    16 | EXPORT-VALIDATION-STANDARD.md       | Export validation requirements     |

---

# Phase 5 — Engineering Standards

| Order | Document                   | Purpose                  |
| ----: | -------------------------- | ------------------------ |
|    17 | ERROR-HANDLING-STANDARD.md | Error handling policy    |
|    18 | THREADING-STANDARD.md      | Threading rules          |
|    19 | JSON-SCHEMA-STANDARD.md    | JSON schema requirements |

---

# Phase 6 — Build & Release Engineering

| Order | Document                            | Purpose                       |
| ----: | ----------------------------------- | ----------------------------- |
|    20 | BUILD-SPECIFICATION.md              | Official build specification  |
|    21 | BUILD-DEVELOPER-GUIDE.md            | Developer build guide         |
|    22 | BUILD-VALIDATION-STANDARD.md        | Build validation requirements |
|    23 | NUITKA-BUILD-STANDARD.md            | Nuitka build rules            |
|    24 | GITHUB-ACTIONS-STANDARD.md          | GitHub Actions policy         |
|    25 | GITHUB-RELEASE-STANDARD.md          | GitHub Release policy         |
|    26 | RELEASE-AUTOMATION-SPECIFICATION.md | Automated release process     |
|    27 | RELEASE-ASSET-STANDARD.md           | Release asset requirements    |
|    28 | VERSIONING-STANDARD.md              | Version management            |
|    29 | CHANGELOG-STANDARD.md               | CHANGELOG policy              |

---

# Phase 7 — Release Stabilization

| Order | Document                          | Purpose                   |
| ----: | --------------------------------- | ------------------------- |
|    30 | IMPLEMENTATION-PROTOCOL-v0.2.0.md | Development protocol      |
|    31 | ARCHITECTURE-FREEZE-v0.2.0.md     | Architecture freeze rules |
|    32 | TEST-PLAN-v0.2.0.md               | Official QA plan          |
|    33 | MIGRATION-v0.2.0.md               | Upgrade guide             |

---

# Phase 8 — AI Development

| Order | Document                              | Purpose                      |
| ----: | ------------------------------------- | ---------------------------- |
|    34 | AI-DEVELOPMENT-GUIDELINES.md          | AI implementation rules      |
|    35 | CONTEXTVAULT-AI-ZERO-FREEDOM-RULES.md | AI restrictions              |
|    36 | AI-DEVELOPMENT-PROMPT.md              | Master AI development prompt |
|    37 | AI-CODE-REVIEW-PROMPT.md              | AI review prompt             |
|    38 | AI-FORENSIC-AUDIT-PROMPT.md           | AI forensic audit prompt     |

---

# Phase 9 — Release Management

| Order | Document             | Purpose                            |
| ----: | -------------------- | ---------------------------------- |
|    39 | RELEASE-CHECKLIST.md | Final production release checklist |

---

# Documentation Categories

## Foundation

Defines the project's vision, architecture, and engineering philosophy.

---

## Feature Specifications

Defines the official functionality of ContextVault.

---

## Technology Freeze

Defines the approved technology stack and prevents unauthorized architectural changes.

---

## Export Engine

Defines the browser automation workflow, export process, DOM observation, compatibility requirements, and export validation.

---

## Engineering Standards

Defines implementation rules that apply throughout the codebase.

---

## Build & Release Engineering

Defines how the application is built, validated, packaged, versioned, and released.

---

## Release Stabilization

Defines the implementation, architecture freeze, testing, and migration requirements for the current release cycle.

---

## AI Development

Defines how AI systems develop, review, audit, and maintain ContextVault.

---

## Release Management

Defines the final production release approval process.

---

# Documentation Statistics

| Category                    | Documents |
| --------------------------- | --------: |
| Foundation                  |         3 |
| Feature Specifications      |         3 |
| Technology Freeze           |         5 |
| Export Engine               |         5 |
| Engineering Standards       |         3 |
| Build & Release Engineering |        10 |
| Release Stabilization       |         4 |
| AI Development              |         5 |
| Release Management          |         1 |
| **Total**                   |    **39** |

---

# Documentation Dependency Flow

```text
Project Foundation
        │
        ▼
Project Architecture
        │
        ▼
Feature Specifications
        │
        ▼
Technology Freeze
        │
        ▼
Export Engine
        │
        ▼
Engineering Standards
        │
        ▼
Implementation Protocol
        │
        ▼
Testing
        │
        ▼
Build Validation
        │
        ▼
GitHub Actions
        │
        ▼
GitHub Release
        │
        ▼
Migration
        │
        ▼
Release Checklist
```

---

# AI Development Workflow

```text
Read INDEX
        │
        ▼
Read Foundation
        │
        ▼
Read Feature Specifications
        │
        ▼
Read Technology Freeze
        │
        ▼
Read Export Engine Specifications
        │
        ▼
Read Engineering Standards
        │
        ▼
Read Build & Release Documentation
        │
        ▼
Read AI Development Documents
        │
        ▼
Implement
        │
        ▼
Run Test Plan
        │
        ▼
Validate Build
        │
        ▼
Update Documentation
        │
        ▼
Complete Release Checklist
        │
        ▼
Publish Release
```

---

# Status Legend

| Status       | Meaning                                    |
| ------------ | ------------------------------------------ |
| ✅ Active    | Official document currently in use         |
| 🔒 Frozen    | Cannot be modified without formal approval |
| ⚠ Deprecated | Retained for compatibility                 |
| ❌ Archived  | Historical reference only                  |

---

# Governance

These documents are the official engineering specifications for ContextVault.

If implementation conflicts with these specifications, the documentation SHALL take precedence until officially updated.

---

# Change Management

Whenever an engineering specification is modified:

- Review affected documentation
- Update dependent specifications if required
- Update CHANGELOG when applicable
- Verify implementation compatibility
- Validate related documentation
- Complete review before merging

---

# Intended Audience

This documentation is intended for:

- Project Maintainers
- Contributors
- Software Engineers
- QA Engineers
- Code Reviewers
- Security Auditors
- Release Managers
- DevOps Engineers
- AI Development Systems

---

# Definition of Done

The engineering documentation is considered complete when every implementation, build, validation, release, and AI-assisted development activity can be performed using the specifications contained within this directory without ambiguity or contradiction.

---

# Final Statement

The `project/` directory is the engineering governance layer of ContextVault.

It defines the project's architecture, engineering standards, feature specifications, technology decisions, export engine behavior, build system, release workflow, testing strategy, documentation policy, and AI development rules.

All future development SHALL comply with the specifications indexed by this document.
