# Project Structure Standard

## Overview

This document defines the repository architecture standard for this project.

It describes the purpose and responsibility of each top-level folder and establishes a consistent organizational structure that is easy for developers, contributors, and AI assistants to understand.

This document is **not project-specific**. Instead, it serves as a reusable architecture guideline that can be adapted to projects of different sizes and technologies.

---

# Design Principles

The repository follows a responsibility-based architecture.

Each folder exists for a single purpose.

The primary goals are:

- Keep the repository clean and predictable.
- Separate source code from documentation and resources.
- Minimize ambiguity when adding new files.
- Make the repository easy to navigate.
- Support long-term maintenance.
- Remain language and framework independent.

---

# Architecture Rules

The following rules should always be followed whenever possible.

1. One folder should have one clear responsibility.
2. Every file should have one permanent home.
3. Avoid creating unnecessary top-level folders.
4. Keep source code separate from documentation.
5. Keep static resources separate from source code.
6. Do not commit generated build artifacts unless intentionally required.
7. Prefer extending existing folders over creating new ones.
8. Keep the repository structure consistent over time.

---

# Standard Repository Structure

```text
.
├── .github/
├── assets/
├── config/
├── data/
├── docs/
├── examples/
├── project/
├── scripts/
├── src/
├── tests/
│
├── .gitignore
├── CHANGELOG.md
├── LICENSE
├── PROJECT_STRUCTURE.md
├── pyproject.toml
└── README.md
```

---

# Folder Responsibilities

## src/

Application source code.

Contains all production code including application logic, UI, business logic, services, models, utilities and runtime components.

---

## assets/

Static resources used by the application.

Typical contents:

- Icons
- Images
- Fonts
- Themes

---

## config/

Application configuration.

Typical contents:

- Configuration files
- Default settings
- Environment configuration
- Logging configuration

---

## data/

Application runtime data.

Typical contents:

- Templates
- Sample data
- Import files
- Export files
- Local databases
- Runtime resources

---

## docs/

End-user documentation.

Documentation should remain organized by topic instead of implementation details.

Recommended categories include:

- Getting Started
- Guides
- Features
- Configuration
- Tutorials
- API
- FAQ
- Troubleshooting
- Release Notes

Documentation should remain compatible with documentation generators such as Docusaurus whenever practical.

---

## project/

Internal project documentation.

Typical contents:

- Architecture
- Specifications
- Research
- Design Decisions
- Roadmaps
- Technical Notes
- Diagrams

This folder is intended primarily for contributors rather than end users.

---

## examples/

Example projects and sample usage.

Useful for demonstrating recommended implementation patterns.

---

## scripts/

Development automation.

Typical contents:

- Setup scripts
- Build scripts
- Test scripts
- Release scripts
- Maintenance utilities

---

## tests/

Automated testing.

Typical contents:

- Unit tests
- Integration tests
- End-to-end tests
- Test fixtures

---

## .github/

GitHub-specific configuration.

Typical contents:

- GitHub Actions
- Issue Templates
- Pull Request Templates
- Funding Configuration
- Repository Workflows

---

# Root Files

## README.md

Repository introduction.

Provides an overview of the project, installation instructions, basic usage and useful links.

---

## CHANGELOG.md

Public history of significant project changes.

---

## LICENSE

Project license.

---

## PROJECT_STRUCTURE.md

Defines the repository architecture standard.

---

## pyproject.toml

Primary Python project configuration.

For non-Python projects, this file should be replaced by the appropriate package or build configuration.

---

## .gitignore

Specifies files and directories that should not be tracked by Git.

---

# Customization Policy

This repository structure is intended as a universal starting point.

Projects are allowed to:

- Add new folders.
- Remove unused folders.
- Rename folders when appropriate.
- Extend folder hierarchies.

However, any customization should preserve clear responsibilities and maintain a logical architecture.

When structural changes are introduced, this document should also be updated.

---

# Optional vs Required

| Component | Recommendation |
|-----------|----------------|
| src | Required |
| README.md | Required |
| LICENSE | Required |
| .gitignore | Required |
| PROJECT_STRUCTURE.md | Recommended |
| tests | Recommended |
| docs | Recommended |
| scripts | Optional |
| examples | Optional |
| project | Optional |
| assets | Optional |
| config | Optional |
| data | Optional |

---

# Guidelines for Contributors

Before creating a new file, determine its responsibility and place it in the most appropriate existing folder.

Avoid introducing new top-level folders unless there is a clear architectural reason.

Maintain consistency throughout the repository.

---

# Guidelines for AI Assistants

AI contributors should:

- Respect existing folder responsibilities.
- Prefer existing folders before creating new ones.
- Avoid unnecessary structural changes.
- Keep generated code organized.
- Update this document whenever repository architecture changes.

---

# Final Note

A repository structure should evolve with the project, but its architecture should remain understandable, predictable and maintainable.

Consistency is generally more valuable than constantly reorganizing folders.

This document serves as the single source of truth for repository organization.