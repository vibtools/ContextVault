# 🏗️ ContextVault — Project Architecture

> **Version:** 1.0 (Frozen)

This document defines the official software architecture of the ContextVault project.

It is the single source of truth for the project's architecture and module relationships.

Every implementation must conform to this document.

---

# 🎯 Architecture Goals

The architecture is designed to be

* Modular
* Maintainable
* Scalable
* Thread Safe
* Portable
* Testable
* Production Ready

Every component must have a single responsibility.

---

# Core Design Principles

The project follows these engineering principles:

* Separation of Concerns
* Single Responsibility Principle (SRP)
* Composition over Inheritance
* Dependency Inversion
* Explicit Data Flow
* Immutable Data where practical
* Standard Library First
* Deterministic Build
* Portable Runtime

---

# High-Level Architecture

```text
                    User
                      │
                      ▼
             CustomTkinter UI
                      │
                      ▼
             UI Controller Layer
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
 Event Dispatcher            Background Queue
                                       │
                                       ▼
                             ThreadPoolExecutor
                                       │
                                       ▼
                                Worker Thread
                                       │
                                       ▼
                             asyncio Event Loop
                                       │
                                       ▼
                           Playwright Automation
                                       │
                                       ▼
                              Google Chrome
                                       │
                                       ▼
                             HTML / DOM Content
                                       │
                                       ▼
                              Parser Layer
                                       │
                                       ▼
                            Internal Data Models
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
             Archive Builder                     Export Services
                     │                                   │
                     └─────────────────┬─────────────────┘
                                       ▼
                                 File System
                                       │
                                       ▼
                              Portable Archive
```

---

# Layered Architecture

The project is divided into independent layers.

Each layer has a clearly defined responsibility.

A layer may only communicate with adjacent layers.

---

## 1. Presentation Layer

Responsible for

* Windows
* Dialogs
* Widgets
* Menus
* Progress Bars
* Notifications
* User Input

Technology

* CustomTkinter

The UI must never perform business logic.

---

## 2. Controller Layer

Responsible for

* User actions
* Request validation
* Workflow orchestration
* Job scheduling

The controller coordinates the application.

It does not perform heavy processing.

---

## 3. Worker Layer

Responsible for

* Long-running operations
* Background jobs
* Export processing
* Browser operations

Technology

* ThreadPoolExecutor
* threading
* asyncio

---

## 4. Browser Layer

Responsible for

* Browser lifecycle
* Profile loading
* Session management
* Navigation
* DOM access

Technology

* Playwright
* Google Chrome

Only this layer communicates with the browser.

---

## 5. Parser Layer

Responsible for

* HTML parsing
* DOM extraction
* Markdown conversion
* Image discovery
* Metadata extraction

No UI code belongs here.

---

## 6. Model Layer

Responsible for

* Data models
* Validation
* Serialization
* Business entities

Technology

* dataclasses
* Pydantic

---

## 7. Archive Layer

Responsible for

* Archive generation
* Manifest creation
* Metadata generation
* Packaging

The archive layer must not depend on UI components.

---

## 8. Service Layer

Provides reusable services such as

* Logging
* Configuration
* File management
* Image processing
* Utility functions

Services should remain stateless whenever practical.

---

## 9. Infrastructure Layer

Responsible for

* File system access
* Runtime paths
* Configuration loading
* External resources

Only this layer should interact directly with the operating system.

---

# Data Flow

Official data flow

```text
User

↓

UI

↓

Controller

↓

Worker Queue

↓

Worker Thread

↓

Playwright

↓

HTML

↓

Parser

↓

Structured Models

↓

Archive Builder

↓

ZIP Package

↓

Export Complete
```

The flow must remain one-directional.

Avoid circular dependencies.

---

# Threading Architecture

Approved execution flow

```text
UI Thread

↓

Queue

↓

ThreadPoolExecutor

↓

Worker Thread

↓

asyncio

↓

Playwright

↓

Parser

↓

Archive Builder

↓

Progress Events

↓

UI Thread
```

Heavy work must never execute on the UI thread.

---

# Module Responsibilities

## app/

Application startup

* Bootstrapping
* Dependency initialization
* Application lifecycle

---

## ui/

Responsible for

* Windows
* Components
* Themes
* Dialogs
* User interaction

---

## controllers/

Responsible for

* Application workflows
* User actions
* Task scheduling

---

## core/

Responsible for

* Core business logic
* Archive engine
* Processing pipeline

---

## browser/

Responsible for

* Playwright
* Chrome
* Sessions
* Navigation

---

## parsers/

Responsible for

* HTML
* DOM
* Markdown
* Images
* Metadata

---

## models/

Responsible for

* Domain models
* Validation
* Serialization

---

## services/

Responsible for

* Reusable services
* Logging
* Configuration
* File utilities

---

## utils/

Contains

* Small helper utilities
* Pure helper functions

Utility modules must not contain business logic.

---

## config/

Contains

* Default configuration
* Constants
* Version information
* Runtime settings

---

## assets/

Contains

* Icons
* Images
* Themes
* Fonts

No source code belongs here.

---

# Dependency Rules

Allowed dependency direction

```text
UI

↓

Controllers

↓

Core

↓

Browser / Parser

↓

Models

↓

Services

↓

Infrastructure
```

Forbidden

* Circular dependencies
* Cross-layer shortcuts
* UI importing browser internals
* Browser importing UI

---

# Runtime Architecture

Portable layout

```text
ContextVault/

│

├── ContextVault.exe

├── Runtime DLLs

├── runtime/

│   ├── assets/

│   ├── config/

│   ├── schemas/

│   ├── templates/

│   ├── themes/

│   └── ...

│

└── logs/
```

No runtime file should require manual installation after extraction.

---

# Build Architecture

Official build flow

```text
Git Push

↓

GitHub Actions

↓

Setup Python

↓

Install Locked Dependencies

↓

Validate Environment

↓

Build (Nuitka)

↓

OneDir

↓

Package ZIP

↓

GitHub Release
```

Every build must be reproducible.

---

# Configuration Architecture

Configuration priority

```text
Default Settings

↓

Configuration Files

↓

Environment Detection

↓

Runtime State
```

Never hardcode environment-specific values.

---

# Error Flow

```text
Exception

↓

Logger

↓

Recovery Strategy

↓

User Notification

↓

Continue or Exit Safely
```

Silent failures are prohibited.

---

# Logging Architecture

Every major operation should generate structured logs.

Recommended levels

* DEBUG
* INFO
* WARNING
* ERROR
* CRITICAL

Logs should help reproduce issues without exposing sensitive information.

---

# Security Boundaries

Never allow

* UI direct file manipulation
* UI direct browser manipulation
* Arbitrary file execution
* Unvalidated external input
* Hardcoded secrets

Every external input must be validated before use.

---

# Architectural Constraints

The following are frozen and must not be changed without an approved architecture revision:

* Folder structure
* Module boundaries
* Layer responsibilities
* Browser architecture
* UI architecture
* Threading architecture
* Build architecture
* Runtime layout
* Dependency direction

---

# Architecture Compliance

Every pull request must answer **YES** to all of the following:

* Does it preserve the layered architecture?
* Does it maintain single responsibility?
* Does it avoid circular dependencies?
* Does it keep the UI thread responsive?
* Does it preserve the approved browser architecture?
* Does it maintain the approved runtime layout?
* Does it remain compatible with GitHub Actions?
* Does it remain compatible with Nuitka OneDir?
* Does it avoid unauthorized dependencies?

If any answer is **NO**, the implementation must be revised before merging.

---

# Final Architecture Rule

ContextVault follows a **Specification-Driven Architecture**.

Developers and AI assistants must implement the approved architecture exactly as defined.

The architecture is considered **frozen**.

Optimization is encouraged only when it preserves:

* Architecture
* Build Reliability
* Runtime Compatibility
* Maintainability
* Performance
* Long-term Stability

No implementation may sacrifice architectural integrity for short-term convenience.
