# 📘 ContextVault Engineering Documentation

This directory contains the official engineering documentation for **ContextVault**.

It serves as the project's **single source of truth** for architecture, engineering standards, implementation rules, release processes, quality assurance, and AI-assisted development.

Every contributor, maintainer, reviewer, and AI system MUST follow the documents contained in this directory.

---

# Purpose

The documentation in this directory exists to ensure that ContextVault remains:

- Architecture-driven
- Deterministic
- Production-ready
- Maintainable
- Secure
- Consistent
- Testable
- Fully documented
- AI-assisted development friendly

No implementation, refactoring, release, or automation workflow should contradict the specifications defined here.

---

# Documentation Categories

The documentation is organized into the following major categories.

## 1. Project Foundation

Defines the overall architecture and engineering principles.

- PROJECT-OVERVIEW.md
- PROJECT-ARCHITECTURE.md
- PROJECT-CODING-STANDARDS.md

---

## 2. Feature Specifications

Defines the official product functionality.

- FEATURE-FREEZE-SPECIFICATION.md
- CONTEXTVAULT-UI-FEATURE-FREEZE.md
- ARCHIVE-FORMAT-FREEZE-SPECIFICATION.md

These documents define what the application is expected to do.

---

## 3. Technology Freeze

Defines the approved technology stack.

- CONTEXTVAULT-OFFICIAL-UI-TECHNOLOGY-FREEZE.md
- CONTEXTVAULT-BROWSER-AUTOMATION-TECHNOLOGY-FREEZE.md
- CONTEXTVAULT-OFFICIAL-MODULES-AND-DEPENDENCIES-FREEZE.md
- CONTEXTVAULT-BUILD-AND-RELEASE-PIPELINE-FREEZE.md
- DEPENDENCY-INTEGRITY-AND-BUILD-RELIABILITY-POLICY.md

These documents prevent uncontrolled technology changes.

---

## 4. Engineering Standards

Defines implementation rules used throughout the project.

- ERROR-HANDLING-STANDARD.md
- THREADING-STANDARD.md
- JSON-SCHEMA-STANDARD.md
- EXPORT-VALIDATION-STANDARD.md
- CHATGPT-COMPATIBILITY-STANDARD.md
- CHATGPT-DOM-OBSERVATION-STANDARD.md

These standards apply to all production code.

---

## 5. Export Engine Specifications

Defines the architecture of the export engine.

- BUGFIX-v0.2.0.md
- EXPORT-ENGINE-SPECIFICATION.md

These documents govern export reliability and browser automation behavior.

---

## 6. Build & Release Engineering

Defines how ContextVault is built, tested, validated, packaged, and released.

- BUILD-SPECIFICATION.md
- BUILD-DEVELOPER-GUIDE.md
- NUITKA-BUILD-STANDARD.md
- BUILD-VALIDATION-STANDARD.md
- GITHUB-ACTIONS-STANDARD.md
- GITHUB-RELEASE-STANDARD.md
- RELEASE-AUTOMATION-SPECIFICATION.md
- RELEASE-ASSET-STANDARD.md
- VERSIONING-STANDARD.md
- CHANGELOG-STANDARD.md

These documents define the official release pipeline.

---

## 7. Release Stabilization (v0.2.0)

Defines the stabilization requirements for the v0.2.0 release.

- IMPLEMENTATION-PROTOCOL-v0.2.0.md
- ARCHITECTURE-FREEZE-v0.2.0.md
- TEST-PLAN-v0.2.0.md
- MIGRATION-v0.2.0.md

These documents govern the implementation and validation of the v0.2.0 stabilization release.

---

## 8. AI Development

Defines how AI systems should work with this repository.

- AI-DEVELOPMENT-GUIDELINES.md
- CONTEXTVAULT-AI-ZERO-FREEDOM-RULES.md
- AI-DEVELOPMENT-PROMPT.md
- AI-CODE-REVIEW-PROMPT.md
- AI-FORENSIC-AUDIT-PROMPT.md

AI implementations MUST comply with all engineering standards before modifying source code.

---

## 9. Release Management

Defines the final release approval process.

- RELEASE-CHECKLIST.md

No production release should be published without completing the release checklist.

---

# Recommended Reading Order

New contributors should read the documentation in the following order.

## Phase 1 — Project Understanding

1. PROJECT-OVERVIEW.md
2. PROJECT-ARCHITECTURE.md
3. PROJECT-CODING-STANDARDS.md

---

## Phase 2 — Product Definition

4. FEATURE-FREEZE-SPECIFICATION.md
5. CONTEXTVAULT-UI-FEATURE-FREEZE.md
6. ARCHIVE-FORMAT-FREEZE-SPECIFICATION.md

---

## Phase 3 — Technology

7. Technology Freeze documents

---

## Phase 4 — Engineering

8. Engineering Standards

---

## Phase 5 — Export Engine

9. Export Engine Specifications

---

## Phase 6 — Build & Release

10. Build & Release Engineering documents

---

## Phase 7 — Release Stabilization

11. Architecture Freeze
12. Implementation Protocol
13. Test Plan
14. Migration Guide

---

## Phase 8 — AI Development

15. AI Development documents

---

## Phase 9 — Release

16. Release Checklist

---

# Modification Policy

These documents are considered official engineering specifications.

Any significant modification SHOULD include:

- Architecture review
- Documentation review
- Version update (if applicable)
- CHANGELOG update
- Release note update
- Validation review

Documentation and implementation SHALL remain synchronized.

---

# AI Usage

When using AI to modify ContextVault:

- Provide these documents as project context.
- Follow every applicable engineering standard.
- Preserve the frozen architecture.
- Preserve public interfaces.
- Preserve compatibility.
- Update documentation together with implementation.
- Execute the required validation process before release.

AI systems MUST NOT introduce undocumented behavior or violate any approved engineering specification.

---

# Governance

This directory is the authoritative reference for:

- Project Architecture
- Feature Scope
- Technology Decisions
- Engineering Standards
- Export Engine Design
- Build Pipeline
- Release Process
- Quality Assurance
- AI Development Rules

If implementation conflicts with these documents, the documentation takes precedence until officially updated.

---

# Engineering Principles

All development should follow these principles:

- Architecture before implementation
- Specification before coding
- Validation before release
- Documentation before completion
- Compatibility before optimization
- Quality before velocity

---

# Final Note

The `project/` directory represents the engineering governance layer of ContextVault.

Its purpose is to ensure that every release remains consistent, reliable, maintainable, fully documented, and reproducible across future development cycles while providing a stable foundation for both human contributors and AI-assisted engineering.
