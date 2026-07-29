# 🧵 ContextVault — Threading Standard

> **Version:** 1.0 (Frozen)

This document defines the official threading and concurrency architecture for the ContextVault project.

All background processing, browser automation, parsing, exporting, and long-running operations must follow these standards.

These rules apply to:

* Human Developers
* AI Coding Assistants
* GitHub Copilot
* ChatGPT
* Codex
* Claude
* Gemini
* DeepSeek

---

# 🎯 Primary Objectives

The threading architecture must ensure that the application remains:

* Responsive
* Stable
* Predictable
* Thread Safe
* Recoverable
* Production Ready

At no time should background work cause the UI to freeze.

---

# Core Principles

The project follows these concurrency principles:

* UI First
* Non-Blocking Execution
* Single UI Thread
* Background Worker Execution
* Message-Based Communication
* Controlled Resource Ownership
* Graceful Cancellation
* Deterministic Task Lifecycle

---

# Official Concurrency Stack

The approved concurrency technologies are:

* threading
* concurrent.futures.ThreadPoolExecutor
* asyncio
* queue.Queue
* threading.Event
* threading.Lock (only when required)

No other concurrency framework may be introduced without an approved architecture update.

---

# High-Level Execution Flow

```text
User Action
      │
      ▼
UI Event
      │
      ▼
Controller
      │
      ▼
Task Queue
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
Playwright
      │
      ▼
Parser
      │
      ▼
Archive Builder
      │
      ▼
Progress Event
      │
      ▼
UI Thread
```

---

# UI Thread Rules

The UI Thread is reserved exclusively for:

* Window rendering
* Widget updates
* User interaction
* Progress display
* Notifications
* Status updates

The UI Thread must never perform:

* Browser automation
* HTML parsing
* Image processing
* Archive creation
* File compression
* File copying
* Long-running loops
* Network operations
* Heavy file I/O

A responsive UI is mandatory.

---

# Worker Thread Rules

Worker Threads are responsible for:

* Browser automation
* Export pipeline
* Parsing
* File operations
* Compression
* Metadata generation
* Background validation
* Long-running processing

Worker Threads must never modify UI widgets directly.

---

# ThreadPoolExecutor Standard

The project uses a centralized ThreadPoolExecutor.

Requirements:

* Create one managed executor.
* Reuse it throughout the application.
* Shut it down gracefully during application exit.

Avoid creating multiple executors unnecessarily.

---

# Queue Standard

All communication between Workers and the UI should occur through queues or controlled event dispatching.

Queues may carry:

* Progress updates
* Status changes
* Completion events
* Errors
* Cancellation events

Workers should not call UI functions directly.

---

# Asyncio Standard

asyncio is used only where asynchronous APIs are required.

Approved usage:

* Playwright
* Async file workflows (if adopted)
* Future async integrations

Never create nested event loops.

Each Worker should own and manage its event loop when required.

---

# Task Lifecycle

Every task follows this lifecycle:

```text
Created
    │
Queued
    │
Started
    │
Running
    │
Completed
```

or

```text
Running
    │
Cancelled
```

or

```text
Running
    │
Failed
```

Every task must end in a defined terminal state.

---

# Cancellation Standard

Long-running tasks must support cancellation.

Cancellation must:

* Stop safely.
* Release resources.
* Close browser contexts.
* Update task status.
* Notify the UI.

Never terminate threads forcefully.

Use cooperative cancellation with:

* threading.Event
* asyncio cancellation

---

# Progress Reporting

Background tasks should periodically report:

* Current stage
* Percentage
* Current item
* Estimated remaining work (when possible)

Progress reporting should not flood the UI.

---

# Resource Ownership

Each Worker owns the resources it creates.

Examples:

* Browser
* Browser Context
* Page
* File Handle
* Temporary Directory

The creating Worker is responsible for cleanup.

---

# Shared State Rules

Shared mutable state should be minimized.

Preferred:

* Immutable objects
* Message passing
* Local variables

If shared state is unavoidable:

* Protect it with synchronization primitives.
* Keep the locked region as small as possible.

---

# Lock Usage

Use threading.Lock only when necessary.

Never lock the UI Thread.

Never hold a lock during:

* Browser operations
* File I/O
* Network requests
* Long-running processing

Locks should protect only critical sections.

---

# Deadlock Prevention

Avoid:

* Nested locks
* Circular lock dependencies
* Waiting on UI while holding locks
* Blocking callbacks

Design for lock-free communication whenever possible.

---

# Race Condition Prevention

Never assume execution order between threads.

Always synchronize shared mutable data.

Use queues instead of direct shared variables whenever practical.

---

# Browser Thread Rules

Each browser session belongs to one Worker.

Never share:

* Browser Context
* Page
* Playwright objects

between concurrent Worker Threads.

---

# File System Rules

Concurrent file operations must avoid:

* Simultaneous writes to the same file
* Partial overwrites
* Inconsistent archive generation

Generate output atomically whenever practical.

---

# Error Propagation

Worker exceptions must never disappear.

Every Worker failure must:

* Be logged
* Be reported
* Update task state
* Notify the Controller
* Notify the UI when appropriate

The application should continue operating whenever recovery is possible.

---

# Shutdown Procedure

Application shutdown must:

1. Stop accepting new tasks.
2. Signal cancellation.
3. Wait for Workers to finish safely.
4. Close browser resources.
5. Flush logs.
6. Shut down ThreadPoolExecutor.
7. Exit cleanly.

Never abandon active Workers.

---

# Performance Guidelines

Avoid:

* Creating unnecessary threads
* Excessive context switching
* Busy waiting
* Infinite polling
* Duplicate browser launches

Reuse resources when appropriate.

---

# AI Threading Requirements

AI-generated code must:

* Preserve the approved threading architecture.
* Keep the UI responsive.
* Use ThreadPoolExecutor correctly.
* Use queues for communication.
* Respect Worker ownership.
* Avoid race conditions.
* Avoid deadlocks.
* Avoid blocking the UI.

AI must never move heavy work back into the UI thread.

---

# Code Review Checklist

Verify:

* No blocking work on the UI thread.
* Worker lifecycle is complete.
* Queue communication is used.
* Cancellation is supported.
* Resources are released.
* Exceptions are propagated.
* Locks are minimal.
* No race conditions are introduced.
* No deadlocks are possible.
* Browser objects are not shared across threads.

---

# Forbidden Practices

Never:

* Update UI directly from Worker Threads.
* Block the UI thread.
* Create unmanaged threads.
* Kill threads forcefully.
* Ignore Worker exceptions.
* Share Playwright Page or Browser Context between Workers.
* Use busy loops for synchronization.
* Leave Workers running during application shutdown.
* Access shared mutable state without synchronization.

---

# Final Standard

ContextVault follows a **Single UI Thread + Managed Background Worker Architecture**.

Every long-running operation must execute outside the UI thread.

Every Worker must have a well-defined lifecycle.

Every shared resource must have a clear owner.

Every task must complete, fail, or cancel predictably.

The responsiveness of the user interface is a non-negotiable requirement and must never be compromised by background processing.
