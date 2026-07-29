# 📑 Project Specification Index

This document serves as the master index for all engineering specifications contained in the `project/` directory.

It provides a quick overview of each document, its purpose, current status, and its role within the ContextVault engineering ecosystem.

---

# Project Information

| Property              | Value                      |
| --------------------- | -------------------------- |
| Project               | ContextVault               |
| Directory             | `/project`                 |
| Purpose               | Engineering Specifications |
| Status                | Active                     |
| Maintainer            | Vib Tools                  |
| Specification Version | 1.0                        |

---

# Reading Order

The recommended reading sequence for new contributors, maintainers, reviewers, and AI systems.

| Order | Document                                                 |
| ----: | -------------------------------------------------------- |
|     1 | PROJECT-OVERVIEW.md                                      |
|     2 | PROJECT-ARCHITECTURE.md                                  |
|     3 | PROJECT-CODING-STANDARDS.md                              |
|     4 | FEATURE-FREEZE-SPECIFICATION.md                          |
|     5 | CONTEXTVAULT-UI-FEATURE-FREEZE.md                        |
|     6 | ARCHIVE-FORMAT-FREEZE-SPECIFICATION.md                   |
|     7 | CONTEXTVAULT-OFFICIAL-UI-TECHNOLOGY-FREEZE.md            |
|     8 | CONTEXTVAULT-BROWSER-AUTOMATION-TECHNOLOGY-FREEZE.md     |
|     9 | CONTEXTVAULT-OFFICIAL-MODULES-AND-DEPENDENCIES-FREEZE.md |
|    10 | CONTEXTVAULT-BUILD-AND-RELEASE-PIPELINE-FREEZE.md        |
|    11 | DEPENDENCY-INTEGRITY-AND-BUILD-RELIABILITY-POLICY.md     |
|    12 | ERROR-HANDLING-STANDARD.md                               |
|    13 | THREADING-STANDARD.md                                    |
|    14 | JSON-SCHEMA-STANDARD.md                                  |
|    15 | AI-DEVELOPMENT-GUIDELINES.md                             |
|    16 | CONTEXTVAULT-AI-ZERO-FREEDOM-RULES.md                    |
|    17 | AI-DEVELOPMENT-PROMPT.md                                 |
|    18 | AI-CODE-REVIEW-PROMPT.md                                 |
|    19 | AI-FORENSIC-AUDIT-PROMPT.md                              |
|    20 | RELEASE-CHECKLIST.md                                     |

---

# Specification Catalogue

| Document                                                 | Category    | Status    | Purpose                                     |
| -------------------------------------------------------- | ----------- | --------- | ------------------------------------------- |
| PROJECT-OVERVIEW.md                                      | Foundation  | ✅ Active  | Project vision, goals, scope and philosophy |
| PROJECT-ARCHITECTURE.md                                  | Foundation  | ✅ Active  | Overall system architecture                 |
| PROJECT-CODING-STANDARDS.md                              | Engineering | ✅ Active  | Coding conventions and implementation rules |
| FEATURE-FREEZE-SPECIFICATION.md                          | Feature     | 🔒 Frozen | Official feature specification              |
| CONTEXTVAULT-UI-FEATURE-FREEZE.md                        | Feature     | 🔒 Frozen | User interface feature specification        |
| ARCHIVE-FORMAT-FREEZE-SPECIFICATION.md                   | Feature     | 🔒 Frozen | Archive format specification                |
| CONTEXTVAULT-OFFICIAL-UI-TECHNOLOGY-FREEZE.md            | Technology  | 🔒 Frozen | Approved UI technologies                    |
| CONTEXTVAULT-BROWSER-AUTOMATION-TECHNOLOGY-FREEZE.md     | Technology  | 🔒 Frozen | Browser automation technology               |
| CONTEXTVAULT-OFFICIAL-MODULES-AND-DEPENDENCIES-FREEZE.md | Technology  | 🔒 Frozen | Approved modules and dependencies           |
| CONTEXTVAULT-BUILD-AND-RELEASE-PIPELINE-FREEZE.md        | Technology  | 🔒 Frozen | Official build and release pipeline         |
| DEPENDENCY-INTEGRITY-AND-BUILD-RELIABILITY-POLICY.md     | Technology  | 🔒 Frozen | Dependency and build policy                 |
| ERROR-HANDLING-STANDARD.md                               | Engineering | ✅ Active  | Error handling standards                    |
| THREADING-STANDARD.md                                    | Engineering | ✅ Active  | Threading architecture and rules            |
| JSON-SCHEMA-STANDARD.md                                  | Engineering | ✅ Active  | JSON format specification                   |
| AI-DEVELOPMENT-GUIDELINES.md                             | AI          | ✅ Active  | AI implementation guidelines                |
| CONTEXTVAULT-AI-ZERO-FREEDOM-RULES.md                    | AI          | 🔒 Frozen | AI implementation restrictions              |
| AI-DEVELOPMENT-PROMPT.md                                 | AI          | ✅ Active  | Master AI development prompt                |
| AI-CODE-REVIEW-PROMPT.md                                 | AI          | ✅ Active  | AI code review prompt                       |
| AI-FORENSIC-AUDIT-PROMPT.md                              | AI          | ✅ Active  | AI forensic audit prompt                    |
| RELEASE-CHECKLIST.md                                     | Release     | ✅ Active  | Official release verification checklist     |

---

# Category Overview

## Foundation

Defines the project's purpose, architecture, and engineering philosophy.

---

## Feature Specifications

Defines what the application must do.

These documents establish the official functional behavior of ContextVault.

---

## Technology Freeze

Defines approved technologies, modules, dependencies, browser stack, and build pipeline.

Changes require explicit architectural approval.

---

## Engineering Standards

Defines how the software must be implemented.

These standards apply to every source file within the project.

---

## AI Specifications

Defines how AI systems should:

* Develop
* Review
* Audit
* Maintain

the project.

---

## Release

Defines the official production release process.

---

# Status Legend

| Status       | Meaning                               |
| ------------ | ------------------------------------- |
| ✅ Active     | Current and in use                    |
| 🔒 Frozen    | Cannot change without formal approval |
| ⚠ Deprecated | Retained for compatibility            |
| ❌ Archived   | Historical reference only             |

---

# Document Dependencies

```text
PROJECT-OVERVIEW
        │
        ▼
PROJECT-ARCHITECTURE
        │
        ▼
PROJECT-CODING-STANDARDS
        │
        ├─────────────┐
        │             │
        ▼             ▼
Feature Specs    Technology Freeze
        │             │
        └──────┬──────┘
               ▼
Engineering Standards
               ▼
AI Specifications
               ▼
Release Checklist
```

---

# Governance

These specifications are the authoritative engineering reference for ContextVault.

When implementation differs from these documents, the specifications take precedence until they are officially revised.

---

# Version Control

When a specification changes:

* Review the affected documents.
* Update related specifications if necessary.
* Record significant changes in `CHANGELOG.md`.
* Verify compatibility before merging.

---

# Intended Audience

This index is intended for:

* Project Maintainers
* Contributors
* Code Reviewers
* Security Auditors
* QA Engineers
* Release Managers
* AI Development Systems

---

# Final Statement

This index provides a single entry point into the complete ContextVault specification library.

Every engineering decision, implementation, review, and release should be guided by the documents referenced here to ensure consistency, maintainability, security, and long-term project stability.
