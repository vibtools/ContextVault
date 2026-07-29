# 🤝 Contributing to ContextVault

First of all, thank you for your interest in contributing to **ContextVault**.

Whether you are fixing a bug, improving documentation, optimizing performance, or proposing a new feature, your contribution is appreciated.

This document explains the official contribution workflow and development rules for the project.

---

# 📜 Project Philosophy

ContextVault is developed with the following principles:

* Stability over speed
* Quality over quantity
* Architecture before implementation
* Specification before opinion
* Long-term maintainability
* Open collaboration
* Production-ready engineering

Every contribution should improve the project without compromising its architecture.

---

# Before You Start

Before contributing, please read the project documentation.

At minimum, review:

* project/PROJECT-OVERVIEW.md
* project/PROJECT-ARCHITECTURE.md
* project/PROJECT-CODING-STANDARDS.md
* project/THREADING-STANDARD.md
* project/ERROR-HANDLING-STANDARD.md
* project/AI-DEVELOPMENT-GUIDELINES.md
* project/CONTEXTVAULT-AI-ZERO-FREEDOM-RULES.md

These documents define the project's official standards.

---

# Ways to Contribute

You can contribute by:

* Fixing bugs
* Improving performance
* Improving documentation
* Adding tests
* Refactoring existing code
* Improving accessibility
* Improving error handling
* Improving logging
* Reporting bugs
* Suggesting enhancements

---

# Before Opening an Issue

Before opening a new issue:

* Search existing issues.
* Confirm the issue has not already been reported.
* Reproduce the problem.
* Collect relevant logs.
* Provide clear reproduction steps.

Well-written issues help maintainers resolve problems faster.

---

# Feature Requests

Feature requests should include:

* The problem being solved
* Why the feature is useful
* Proposed behavior
* Alternative approaches considered
* Potential implementation concerns

Feature requests do not guarantee implementation.

---

# Development Workflow

The recommended workflow is:

```text
Fork Repository

↓

Create Feature Branch

↓

Implement Changes

↓

Run Local Verification

↓

Run Code Review

↓

Commit Changes

↓

Push Branch

↓

Open Pull Request

↓

Project Review

↓

Merge
```

---

# Branch Naming

Recommended branch names:

```text
feature/archive-export

feature/browser-manager

bugfix/export-timeout

bugfix/parser-error

docs/readme-update

refactor/thread-manager

test/archive-validation
```

Avoid generic names such as:

```text
test

fix

update

new

temp

branch1
```

---

# Commit Message Format

Use clear, descriptive commit messages.

Examples:

```text
feat: add archive metadata validation

fix: prevent browser timeout during export

docs: update project architecture

refactor: simplify worker lifecycle

perf: reduce archive generation time

test: add parser unit tests
```

Avoid:

```text
update

fix

changes

work

new code
```

---

# Pull Request Requirements

Every Pull Request should:

* Explain the purpose of the change.
* Describe the implementation.
* List any breaking changes.
* Reference related issues (if applicable).
* Include screenshots for UI changes (when applicable).

Small, focused pull requests are preferred.

---

# Coding Standards

All code must follow:

* project/PROJECT-CODING-STANDARDS.md
* project/PROJECT-ARCHITECTURE.md
* project/THREADING-STANDARD.md
* project/ERROR-HANDLING-STANDARD.md

Do not submit code that violates these standards.

---

# Architecture Rules

Contributors must not:

* Change the project architecture.
* Replace approved technologies.
* Change the runtime layout.
* Change the build pipeline.
* Introduce unofficial dependencies.

Architectural changes require prior approval.

---

# Approved Technology Stack

The project officially uses:

* Python 3.12+
* CustomTkinter
* Playwright
* Google Chrome
* Nuitka

Do not replace these technologies without an approved architecture revision.

---

# Dependency Policy

Before introducing a new dependency, verify:

* The Python Standard Library cannot solve the problem.
* The dependency is actively maintained.
* The dependency is compatible with the project's license.
* The dependency works with Nuitka.
* The dependency works with GitHub Actions.
* The dependency does not duplicate existing functionality.

Unauthorized dependencies will not be accepted.

---

# Threading Rules

Background work must never execute on the UI thread.

Use the approved architecture:

```text
UI

↓

Queue

↓

ThreadPoolExecutor

↓

Worker

↓

asyncio

↓

Playwright
```

Do not bypass this model.

---

# Error Handling

Do not ignore exceptions.

Every failure should:

* Be handled.
* Be logged.
* Produce meaningful diagnostics.
* Preserve application stability.

Silent failures are prohibited.

---

# Documentation

If your contribution changes public behavior, update the relevant documentation.

This includes:

* README
* CHANGELOG
* Examples
* Project documentation

Documentation should evolve with the code.

---

# Testing

Before submitting a Pull Request, verify that:

* The project builds successfully.
* Existing functionality still works.
* New functionality behaves as expected.
* No regressions were introduced.

If practical, include tests for new functionality.

---

# Build Compatibility

Every contribution must remain compatible with:

* GitHub Actions
* Nuitka OneDir
* Portable Runtime
* Windows

Do not rely on local machine configuration.

---

# AI-Assisted Contributions

AI-generated code is welcome.

However, contributors remain responsible for:

* Reviewing generated code
* Verifying correctness
* Ensuring architectural compliance
* Maintaining code quality

AI output must satisfy the same standards as manually written code.

---

# Code Review

Every contribution may be reviewed for:

* Architecture
* Build compatibility
* Thread safety
* Error handling
* Performance
* Security
* Maintainability
* Documentation

Review decisions are based on project standards, not personal coding preferences.

---

# What Will Likely Be Rejected

Contributions that:

* Break the architecture
* Introduce unnecessary complexity
* Reduce maintainability
* Add unofficial dependencies
* Break GitHub Actions
* Break Nuitka compatibility
* Reduce UI responsiveness
* Introduce security risks
* Violate frozen specifications

---

# Code of Collaboration

Please be:

* Respectful
* Professional
* Constructive
* Patient

Focus discussions on technical merit and objective evidence.

---

# Questions

If you are unsure about a design decision:

* Open a discussion.
* Ask before implementing major changes.
* Reference the relevant project documentation.

It is better to clarify early than to redesign later.

---

# License

By submitting a contribution, you agree that your contribution may be distributed under the same license as the ContextVault project.

---

# Final Note

ContextVault values **quality over quantity**.

A small, well-designed contribution that respects the project's architecture is more valuable than a large change that introduces technical debt.

Thank you for helping make ContextVault a stable, maintainable, and production-ready open-source project.
