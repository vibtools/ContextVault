# EXPORT-ENGINE-SPECIFICATION.md

# ContextVault Export Engine Specification

Version: 1.0

Applies To:

- v0.2.0
- Future Releases

Status:

ENGINEERING SPECIFICATION

---

# Purpose

This document defines the complete architecture, lifecycle, validation rules, and operational behavior of the ContextVault Export Engine.

The Export Engine is responsible for safely collecting, validating, and exporting AI conversations while preserving data integrity.

This specification is the single source of truth for every export operation.

---

# Design Goals

The Export Engine must be:

- Reliable
- Deterministic
- Fault tolerant
- Resume capable
- Thread safe
- Browser independent (where possible)
- Metadata complete
- Large conversation friendly
- Production ready

---

# Core Principles

The Export Engine MUST NEVER:

- Assume page load means conversation readiness.
- Export incomplete conversations.
- Export partial metadata.
- Lose messages.
- Skip attachments.
- Ignore loading states.
- Depend on fixed sleep timers.

Every export must complete only after successful validation.

---

# Export Pipeline

Every export must follow the exact pipeline below.

Browser Launch

↓

Browser Connection

↓

Conversation Selection

↓

Open Conversation

↓

Browser Navigation

↓

DOM Ready

↓

React Ready

↓

Conversation Ready Detection

↓

Dynamic Wait

↓

Conversation Stabilization

↓

Deep Scan

↓

Metadata Collection

↓

Message Collection

↓

Attachment Collection

↓

Image Collection

↓

Code Block Collection

↓

Validation

↓

JSON Generation

↓

Integrity Verification

↓

Save Archive

↓

Export Complete

---

# Conversation Readiness Detection

Conversation readiness is NOT equal to browser readiness.

The Export Engine shall verify:

✓ Browser loaded

✓ DOM loaded

✓ React finished rendering

✓ Conversation container exists

✓ First messages visible

✓ Lazy loading complete

✓ Streaming finished

✓ Continue button absent

✓ Message count stable

✓ Final validation successful

Only then may export begin.

---

# Dynamic Waiting Strategy

The Export Engine shall never use fixed waiting.

Incorrect:

sleep(5)

sleep(10)

sleep(30)

Correct:

Observe the conversation continuously until readiness conditions are satisfied.

Waiting shall stop immediately after all readiness checks pass.

---

# Conversation Stabilization

Large conversations often continue rendering after the page becomes visible.

The engine shall continuously monitor:

- Message count
- DOM mutations
- Scroll height
- React updates
- Lazy loaded elements

Export begins only after stabilization.

---

# Deep Scan

Export consists of multiple scan stages.

Stage 1

Browser Validation

Stage 2

Conversation Validation

Stage 3

Metadata Discovery

Stage 4

Message Discovery

Stage 5

Message Verification

Stage 6

Attachment Discovery

Stage 7

Image Discovery

Stage 8

Code Block Discovery

Stage 9

Markdown Discovery

Stage 10

Final Validation

No stage may be skipped.

---

# Metadata Collection

The Export Engine must collect complete metadata.

Required fields include:

- Conversation ID
- Title
- URL
- Export UUID
- Export Version
- Schema Version
- ContextVault Version
- Browser Name
- Browser Version
- Browser Profile
- ChatGPT Workspace
- ChatGPT Model
- Export Timestamp UTC
- Export Timestamp Local
- Language
- Message Count
- User Messages
- Assistant Messages
- Images
- Attachments
- Code Blocks
- Tables
- Estimated Size

Missing required metadata invalidates the export.

---

# Message Collection

Every conversation message shall include:

- Message ID
- Author
- Role
- Timestamp (if available)
- Markdown
- Plain Text
- HTML (optional)
- Images
- Attachments
- Code Blocks
- Tables
- Citations
- Thinking Blocks (if supported)
- Tool Results (if supported)

Messages must preserve original order.

No message may be omitted.

---

# Large Conversation Support

The Export Engine must support:

- Thousands of messages
- Long code blocks
- Large markdown documents
- Multiple images
- Large attachments
- Professional research conversations

There shall be no artificial message limit.

---

# Retry Strategy

Temporary failures shall trigger automatic retries.

Retry examples:

- Slow network
- Temporary empty DOM
- React rendering delay
- Lazy loading delay
- Browser hiccups

Retries shall use exponential backoff where appropriate.

The engine shall only fail after retry limits are exceeded.

---

# Validation Rules

Before export:

Validate:

✓ Metadata

✓ Messages

✓ Attachments

✓ Images

✓ Code Blocks

✓ JSON Structure

✓ Required Fields

✓ Schema

After export:

Validate:

✓ Archive written

✓ JSON valid

✓ File readable

✓ Metadata complete

✓ Message count matches

Only validated exports are considered successful.

---

# Failure Rules

Export may fail only if:

- Browser crashed
- Conversation unavailable
- Permission denied
- Validation failed
- Retry exhausted
- Storage failure

Loading delays are NOT failures.

Large conversations are NOT failures.

Slow rendering is NOT a failure.

---

# Progress Reporting

The user interface shall report every stage.

Examples:

Launching Browser...

Opening Conversation...

Waiting for ChatGPT...

Detecting Conversation...

Loading Messages...

Conversation Stabilized...

Scanning Messages...

Collecting Metadata...

Collecting Images...

Collecting Attachments...

Validating Export...

Saving Archive...

Export Completed.

Progress messages must accurately reflect the current stage.

---

# Performance Requirements

The Export Engine shall:

- Minimize unnecessary DOM queries.
- Avoid duplicate scanning.
- Avoid busy waiting.
- Reduce memory usage.
- Release browser resources immediately after export.
- Support background execution.

---

# Thread Safety

The Export Engine must be fully thread-safe.

Requirements:

- No shared mutable state.
- Safe cancellation.
- Safe resume.
- Safe shutdown.
- Queue-based communication.
- No UI blocking.

---

# Logging Requirements

Every export shall produce structured logs.

Examples:

Conversation opened.

Conversation stabilized.

Metadata collected.

Messages scanned.

Validation passed.

Archive saved.

Export completed.

Errors must include sufficient diagnostic information for debugging.

---

# Compatibility

The Export Engine shall remain compatible with future ChatGPT UI changes whenever possible.

Implementation must prioritize resilient selectors and adaptive detection strategies.

---

# Release Requirements

An export engine implementation shall not be considered production-ready until:

✓ All validation stages pass.

✓ Metadata is complete.

✓ Large conversations export successfully.

✓ Small conversations continue working.

✓ Retry system passes.

✓ Deep scan passes.

✓ QA passes.

✓ Forensic audit passes.

---

# Definition of Done

The Export Engine is considered complete only when it consistently exports complete, validated, metadata-rich conversation archives regardless of conversation size while preserving stability, correctness, and production reliability.

---

---

# Appendix A — Export State Machine

The Export Engine shall operate as a deterministic state machine.

No state may be skipped.

No export may bypass validation.

Every transition must be logged.

---

## Export Lifecycle

```text
IDLE
    │
    ▼
INITIALIZING
    │
    ▼
LAUNCH_BROWSER
    │
    ▼
CONNECT_BROWSER
    │
    ▼
SCAN_CONVERSATIONS
    │
    ▼
SELECT_CONVERSATION
    │
    ▼
OPEN_CONVERSATION
    │
    ▼
WAIT_BROWSER_READY
    │
    ▼
WAIT_DOM_READY
    │
    ▼
WAIT_REACT_READY
    │
    ▼
WAIT_CONVERSATION_READY
    │
    ▼
WAIT_MESSAGE_STABILIZATION
    │
    ▼
DEEP_SCAN
    │
    ▼
COLLECT_METADATA
    │
    ▼
COLLECT_MESSAGES
    │
    ▼
COLLECT_IMAGES
    │
    ▼
COLLECT_ATTACHMENTS
    │
    ▼
COLLECT_CODE_BLOCKS
    │
    ▼
VALIDATE_EXPORT
    │
    ▼
GENERATE_JSON
    │
    ▼
VERIFY_ARCHIVE
    │
    ▼
SAVE_ARCHIVE
    │
    ▼
EXPORT_COMPLETE
```

---

## Failure State

At any stage, unrecoverable failures transition to:

```text
CURRENT STATE

↓

ERROR DETECTED

↓

LOG ERROR

↓

RETRY (if recoverable)

↓

SUCCESS
     │
     └──────────────► Continue Pipeline

or

FAILED
```

The export engine shall never terminate immediately without evaluating whether the error is recoverable.

---

## Retry Flow

Recoverable failures shall follow the retry pipeline.

```text
Failure

↓

Detect Error Type

↓

Recoverable?

│
├── No
│      ↓
│   FAILED
│
└── Yes
       ↓
Retry

↓

Conversation Ready?

│
├── No
│      ↓
│  Wait Dynamically
│
└── Yes
       ↓
Continue Export
```

---

## Progress State Mapping

The user interface shall always reflect the current export state.

| Engine State               | User Interface Status          |
| -------------------------- | ------------------------------ |
| INITIALIZING               | Initializing Export Engine...  |
| LAUNCH_BROWSER             | Launching Browser...           |
| CONNECT_BROWSER            | Connecting to Browser...       |
| SCAN_CONVERSATIONS         | Scanning Conversations...      |
| SELECT_CONVERSATION        | Selecting Conversation...      |
| OPEN_CONVERSATION          | Opening Conversation...        |
| WAIT_BROWSER_READY         | Waiting for Browser...         |
| WAIT_DOM_READY             | Loading Page...                |
| WAIT_REACT_READY           | Waiting for ChatGPT UI...      |
| WAIT_CONVERSATION_READY    | Detecting Conversation...      |
| WAIT_MESSAGE_STABILIZATION | Waiting for Messages...        |
| DEEP_SCAN                  | Deep Scanning Conversation...  |
| COLLECT_METADATA           | Collecting Metadata...         |
| COLLECT_MESSAGES           | Collecting Messages...         |
| COLLECT_IMAGES             | Collecting Images...           |
| COLLECT_ATTACHMENTS        | Collecting Attachments...      |
| COLLECT_CODE_BLOCKS        | Collecting Code Blocks...      |
| VALIDATE_EXPORT            | Validating Export...           |
| GENERATE_JSON              | Generating Archive...          |
| VERIFY_ARCHIVE             | Verifying Archive...           |
| SAVE_ARCHIVE               | Saving Archive...              |
| EXPORT_COMPLETE            | Export Completed Successfully. |
| FAILED                     | Export Failed.                 |

---

## State Transition Rules

The Export Engine shall satisfy the following rules:

- Every state must complete successfully before the next state begins.
- States must execute in the defined order.
- No state may be skipped.
- The engine shall never transition directly from loading to export.
- Conversation readiness is mandatory before deep scanning.
- Message stabilization is mandatory before metadata collection.
- Metadata collection is mandatory before archive generation.
- Archive verification is mandatory before reporting success.
- Every transition shall be written to the application log.

---

## Recovery Rules

If the export process is interrupted unexpectedly, the engine shall:

- Preserve completed work where possible.
- Resume from the last valid state when supported.
- Avoid rescanning completed stages unnecessarily.
- Prevent duplicate exports.
- Maintain export consistency.

---

## State Machine Invariants

The following conditions must always remain true:

- Export must never start before conversation readiness.
- Message count must never decrease after stabilization.
- Metadata must be complete before archive creation.
- Validation must complete before saving.
- Export success may only be reported after archive verification.
- Partial exports must never be reported as successful.

---

---

# Appendix B — Conversation Readiness Detection Algorithm

## Purpose

This appendix defines the official conversation readiness detection algorithm used by the ContextVault Export Engine.

The purpose of this algorithm is to ensure that export never begins until the ChatGPT conversation has been fully loaded, rendered, stabilized, and validated.

Conversation readiness shall be determined through multiple validation stages rather than a single browser event.

---

# Design Principle

The Export Engine SHALL NEVER assume:

Browser Loaded

=

Conversation Ready

These are independent states.

A browser page may finish loading while ChatGPT continues rendering conversation content.

---

# Readiness Pipeline

The Export Engine shall execute the following pipeline.

```text
Browser Connected
        │
        ▼
Navigation Completed
        │
        ▼
DOM Ready
        │
        ▼
React Application Ready
        │
        ▼
Conversation Container Found
        │
        ▼
Initial Messages Detected
        │
        ▼
Message Count Monitoring
        │
        ▼
Lazy Loading Detection
        │
        ▼
Streaming Detection
        │
        ▼
Conversation Stabilization
        │
        ▼
Deep Validation
        │
        ▼
Conversation Ready
```

---

# Stage 1 — Browser Ready

Verify:

- Browser connected
- Target page opened
- Navigation completed
- No browser crash

Failure at this stage is recoverable.

---

# Stage 2 — DOM Ready

Verify:

- Document loaded
- DOM accessible
- Primary application container exists

DOM readiness is NOT sufficient for export.

---

# Stage 3 — React Ready

Verify:

- React application mounted
- Conversation UI rendered
- Interactive elements available

Rendering may continue after this stage.

---

# Stage 4 — Conversation Container Detection

The Export Engine shall detect:

- Conversation container
- Conversation title
- Conversation body
- Scroll container

If missing:

Continue waiting.

Do not fail.

---

# Stage 5 — Initial Message Detection

Verify that at least one conversation message exists.

If zero messages are detected:

Continue monitoring.

Do not immediately report failure.

---

# Stage 6 — Message Count Monitoring

The Export Engine shall continuously monitor:

Current Message Count

The message count may increase as ChatGPT continues rendering.

The engine shall continue observing while the count changes.

---

# Stage 7 — Lazy Loading Detection

Large conversations frequently load additional messages after scrolling or after React updates.

The Export Engine shall detect:

- Newly inserted messages
- New markdown blocks
- New images
- New code blocks

Export must remain paused while new content continues to appear.

---

# Stage 8 — Streaming Detection

If ChatGPT is still generating or rendering content:

Export must wait.

Streaming indicators include:

- Active generation
- Partial responses
- Rendering placeholders
- Loading indicators

---

# Stage 9 — Conversation Stabilization

Conversation stabilization occurs only after:

- Message count stops increasing
- DOM mutations settle
- Rendering completes
- Scroll height stabilizes
- No new content appears

Only then may export continue.

---

# Stage 10 — Deep Validation

Perform a complete validation.

Verify:

✓ Conversation ID

✓ Title

✓ URL

✓ Metadata

✓ Messages

✓ Images

✓ Attachments

✓ Code Blocks

✓ Tables

✓ Markdown

Any missing required data postpones export until validation succeeds.

---

# Ready State

The conversation is officially considered READY only if:

✓ Browser ready

✓ DOM ready

✓ React ready

✓ Conversation detected

✓ Messages detected

✓ Message count stabilized

✓ Lazy loading complete

✓ Streaming complete

✓ Validation passed

---

# Timeout Policy

The Export Engine shall not use a fixed timeout.

Instead:

Use adaptive waiting.

Small conversations should export immediately.

Large conversations may require significantly more time.

Timeout shall be configurable.

Large conversations must never fail simply because they require additional loading time.

---

# Dynamic Waiting Policy

Incorrect:

sleep(5)

sleep(10)

sleep(30)

Correct:

Observe

↓

Validate

↓

Continue Waiting

↓

Re-evaluate

↓

Export

Waiting shall terminate immediately after readiness is confirmed.

---

# Retry Policy

Recoverable conditions include:

- Temporary network latency
- React rendering delays
- Lazy loading delays
- Temporary empty DOM
- Browser responsiveness

The Export Engine shall automatically retry readiness detection.

---

# Failure Policy

Conversation readiness failure shall occur ONLY IF:

- Browser crashed
- Conversation unavailable
- Permission denied
- Retry limit exceeded
- Validation permanently failed

Slow loading is NOT a failure.

Large conversations are NOT a failure.

Delayed rendering is NOT a failure.

---

# User Interface Requirements

The user interface shall accurately display the current readiness stage.

Examples:

Opening Conversation...

Loading ChatGPT...

Rendering Conversation...

Waiting for Messages...

Detecting New Messages...

Conversation Stabilizing...

Performing Deep Validation...

Conversation Ready.

The application shall never display:

"No conversation messages were found"

until every readiness stage has been completed.

---

# Acceptance Criteria

This algorithm is considered correctly implemented only if:

✓ Small conversations export correctly.

✓ Large conversations export correctly.

✓ Professional multi-thousand message conversations export successfully.

✓ Dynamic waiting replaces fixed waiting.

✓ Message stabilization is detected correctly.

✓ No premature export occurs.

✓ No false failure occurs.

✓ Complete metadata is collected.

✓ Export begins only after readiness confirmation.

---

# End of Appendix B

# Appendix Complete

End of Document
