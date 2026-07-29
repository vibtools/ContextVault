# ⚠️ ContextVault — Error Handling Standard

> **Version:** 1.0 (Frozen)

This document defines the official error handling standard for the ContextVault project.

Every module, service, worker, controller, and UI component must follow these rules.

These standards apply to both human developers and AI-generated code.

---

# 🎯 Primary Objectives

The error handling system must ensure that the application remains

* Stable
* Predictable
* Recoverable
* User Friendly
* Production Ready

Errors should never unexpectedly terminate the application.

Every failure must be handled intentionally.

---

# Core Principles

Every error must be

* Detected
* Classified
* Logged
* Reported
* Recovered (when possible)

Never ignore failures.

Never hide failures.

Never silently continue after critical failures.

---

# Error Classification

All errors should be classified into one of the following categories.

---

## Recoverable Errors

Examples

* Temporary browser timeout
* Temporary network interruption
* Missing optional resource
* Retryable Playwright operation

Action

* Retry when appropriate.
* Log the event.
* Inform the user if needed.
* Continue execution.

---

## User Errors

Examples

* Invalid export path
* Invalid settings
* Missing Chrome installation
* Unsupported file selection
* Permission denied

Action

* Show a clear message.
* Explain how to fix the issue.
* Do not display internal stack traces.

---

## Internal Errors

Examples

* Unexpected parser failure
* Invalid application state
* Data validation failure
* Programming error

Action

* Log detailed information.
* Notify the user that an internal error occurred.
* Safely stop the affected operation.

---

## Fatal Errors

Examples

* Critical configuration missing
* Runtime corruption
* Archive generation failure that compromises output integrity
* Required application resources unavailable

Action

* Stop the affected workflow.
* Preserve user data.
* Generate diagnostic logs.
* Exit gracefully only if recovery is impossible.

---

# Error Severity Levels

Every logged error should use one of the following levels.

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

Severity must accurately reflect the impact.

Avoid overusing CRITICAL.

---

# Exception Handling Rules

Always catch specific exceptions.

Preferred

```python
try:
    ...
except FileNotFoundError:
    ...
except PermissionError:
    ...
```

Avoid

```python
except Exception:
```

unless acting as a controlled boundary.

Never use

```python
except:
    pass
```

or any equivalent silent handling.

---

# Exception Boundaries

Exception boundaries should exist at

* Worker entry points
* Controller entry points
* Background task runners
* Export pipeline
* Browser lifecycle
* Application startup
* Application shutdown

Internal helper functions should generally allow exceptions to propagate upward.

---

# Logging Rules

Every unexpected failure must be logged.

Logs should include

* Timestamp
* Severity
* Module
* Function
* Error type
* Error message
* Context
* Stack trace (where appropriate)

Sensitive information must never be logged.

Do not log

* Passwords
* Tokens
* API Keys
* Secrets
* Personal data unless absolutely required for diagnostics

---

# User Notification Rules

Users should receive messages they can understand.

Good

```text
Unable to save the archive.

Please verify that the selected folder is writable.
```

Bad

```text
PermissionError: [Errno 13]
```

Technical details belong in the logs, not the user interface.

---

# Retry Policy

Only retry operations that are expected to succeed later.

Examples

* Browser navigation
* Temporary file lock
* Network interruption
* Page loading

Do not retry

* Invalid user input
* Missing required configuration
* Programming errors
* Validation failures

Use the approved retry mechanism.

* Tenacity

Do not implement custom retry loops unless specifically required.

---

# Browser Error Handling

Handle

* Browser launch failures
* Page timeouts
* Navigation failures
* Element lookup failures
* Closed browser instances
* Profile loading failures

Always close browser resources safely.

---

# File System Error Handling

Handle

* Missing files
* Missing directories
* Permission denied
* Read failures
* Write failures
* Disk full conditions

Never assume the file system is available.

Always validate before writing.

---

# Configuration Errors

If configuration is invalid

* Explain the issue.
* Identify the affected configuration.
* Stop only the dependent feature.
* Keep the rest of the application operational when possible.

---

# Validation Errors

Validate

* User input
* Configuration
* Metadata
* JSON
* Archive manifest

Reject invalid data early.

Never continue with corrupted input.

---

# Thread Error Handling

Exceptions inside worker threads must never disappear.

Every worker exception must

* be logged,
* be reported to the controller,
* update task status,
* notify the UI if required.

The UI thread must remain alive.

---

# Async Error Handling

Every asyncio task must

* handle cancellation correctly,
* propagate unexpected exceptions,
* release resources,
* close browser contexts safely.

Never leave orphaned tasks.

---

# Cleanup Rules

Every operation must clean up allocated resources.

Always release

* Browser instances
* Browser contexts
* Pages
* File handles
* Streams
* Temporary files
* Locks

Cleanup should execute even after failures.

---

# Partial Failure Policy

If one export item fails

Evaluate whether

* only the failed item should stop, or
* the entire export should stop.

Avoid aborting unrelated work unnecessarily.

---

# Recovery Strategy

Recovery priority

1. Retry
2. Fallback
3. Partial completion
4. Graceful cancellation
5. Safe shutdown

Never corrupt existing user data during recovery.

---

# Build & Release Errors

During GitHub Actions or local builds

Treat the following as release-blocking

* Missing dependency
* Version mismatch
* Build failure
* Packaging failure
* Missing runtime resource
* Failed validation

Never publish a release with unresolved build errors.

---

# AI Error Handling Requirements

AI-generated code must

* use specific exception types,
* preserve stack traces where appropriate,
* avoid silent failures,
* log meaningful diagnostics,
* keep the UI responsive,
* preserve thread safety,
* preserve build compatibility.

AI must never suppress errors simply to make code appear successful.

---

# Code Review Checklist

Verify

* Specific exceptions are used.
* No silent exception handling exists.
* Logging is meaningful.
* User messages are understandable.
* Resources are always released.
* Retry logic is appropriate.
* Thread errors are propagated.
* Async tasks are cleaned up.
* Build failures stop the release process.

---

# Forbidden Practices

Never

* use `except: pass`
* ignore return values indicating failure
* suppress stack traces during debugging
* expose internal exceptions directly to users
* retry non-recoverable errors
* swallow worker thread exceptions
* continue after fatal corruption
* log secrets or credentials

---

# Final Standard

Every error in ContextVault must be handled in a way that improves reliability without compromising correctness.

The application should always:

* fail predictably,
* recover when appropriate,
* preserve user data,
* produce actionable diagnostics,
* and remain suitable for production use.

A hidden error is considered a defect.

A predictable and well-reported error is considered a controlled outcome.
