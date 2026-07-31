# EXPORT-VALIDATION-STANDARD.md

# ContextVault Export Validation Standard

Version: 1.0

Applies To:

- Export Engine
- JSON Export
- Metadata Collection
- Archive Generation
- Validation Layer
- Quality Assurance

Status:

ENGINEERING STANDARD

---

# Purpose

This document defines the mandatory validation process performed before any conversation export is considered successful.

Generating an export file does NOT imply a successful export.

Every exported archive must pass a complete validation process to ensure correctness, completeness, integrity, and long-term usability.

Validation is mandatory.

No export may bypass validation.

---

# Design Principles

The validation system shall be:

- Deterministic
- Complete
- Non-destructive
- Metadata aware
- Schema compliant
- Reproducible
- Thread-safe

---

# Validation Pipeline

Every export shall follow the validation pipeline.

Conversation Ready

↓

Deep Scan Complete

↓

Metadata Validation

↓

Message Validation

↓

Attachment Validation

↓

Image Validation

↓

JSON Validation

↓

Schema Validation

↓

Integrity Validation

↓

Archive Validation

↓

Export Success

---

# Validation Stages

The Export Engine shall perform the following stages.

Stage 1

Conversation Validation

Stage 2

Metadata Validation

Stage 3

Message Validation

Stage 4

Markdown Validation

Stage 5

Code Block Validation

Stage 6

Image Validation

Stage 7

Attachment Validation

Stage 8

JSON Validation

Stage 9

Schema Validation

Stage 10

Integrity Validation

Stage 11

Archive Validation

Stage 12

Final Validation

No validation stage may be skipped.

---

# Conversation Validation

Verify:

✓ Conversation exists

✓ Conversation ID

✓ Title

✓ URL

✓ Conversation body

✓ Export source

Failure invalidates the export.

---

# Metadata Validation

The following metadata is mandatory.

- Conversation ID
- Conversation Title
- Conversation URL
- Export UUID
- Export Timestamp (UTC)
- Export Timestamp (Local)
- ContextVault Version
- Export Engine Version
- Schema Version
- Browser Name
- Browser Version
- Browser Profile
- ChatGPT Model (if available)
- Workspace (if available)
- Language (if detectable)

Missing mandatory metadata shall fail validation.

Metadata shall never be fabricated.

Unknown values must be reported as unavailable.

---

# Message Validation

Every message shall contain:

- Unique Message ID (generated if unavailable)
- Role
- Content
- Order
- Message Index

Verify:

✓ Message order preserved

✓ No duplicated messages

✓ No missing messages

✓ Message count matches conversation

---

# Markdown Validation

Verify:

- headings
- lists
- tables
- block quotes
- links
- formatting

Markdown shall remain valid.

---

# Code Block Validation

Verify:

- language detection
- formatting
- indentation
- multiline preservation
- syntax text

Code shall never be truncated.

---

# Image Validation

Verify:

- image references
- image metadata
- image ordering

Broken image references invalidate validation.

---

# Attachment Validation

Verify:

- attachment existence
- metadata
- filenames
- references

Missing attachment references shall be reported.

---

# JSON Validation

Verify:

✓ Valid JSON

✓ UTF-8 Encoding

✓ No malformed objects

✓ No duplicate keys

✓ No invalid characters

✓ Proper escaping

---

# Schema Validation

Every export shall comply with:

vibproject.ygit

and

the current export schema.

Required fields shall never be omitted.

---

# Integrity Validation

Verify:

✓ Message Count

✓ Metadata Count

✓ Image Count

✓ Attachment Count

✓ Code Block Count

The exported archive must match the scanned conversation.

---

# Archive Validation

Verify:

- Archive created successfully
- Archive readable
- JSON readable
- Export directory writable
- File size greater than zero

---

# Duplicate Validation

The Export Engine shall detect:

- duplicated messages
- duplicated metadata
- duplicated attachments
- duplicated images

Duplicates shall be reported.

---

# Missing Data Validation

Detect:

- missing messages
- missing images
- missing attachments
- missing metadata
- missing references

Validation shall fail if required information is missing.

---

# Export Success Rules

Export is considered successful ONLY IF:

✓ Conversation validation passed.

✓ Metadata validation passed.

✓ Message validation passed.

✓ JSON validation passed.

✓ Schema validation passed.

✓ Archive validation passed.

✓ Integrity validation passed.

---

# Validation Failure Rules

Validation shall fail when:

- invalid JSON
- incomplete metadata
- incorrect message count
- broken archive
- unreadable file
- schema mismatch
- missing required fields

---

# Validation Report

Every export shall generate a structured validation report.

Minimum report sections:

- Conversation Summary
- Metadata Status
- Message Statistics
- Attachment Statistics
- Image Statistics
- Validation Results
- Warnings
- Errors
- Final Verdict

---

# Validation Severity

Every validation result shall be classified.

PASS

WARNING

ERROR

CRITICAL

Only PASS and approved WARNING states allow successful export.

ERROR and CRITICAL invalidate the export.

---

# Logging Requirements

The validation layer shall log:

Validation started.

Metadata validated.

Messages validated.

JSON validated.

Schema validated.

Integrity verified.

Archive verified.

Validation completed.

---

# Thread Safety

Validation shall execute within the Export Worker.

Validation shall never block the user interface.

Communication with the UI shall occur through thread-safe queues.

---

# AI Development Rules

Future implementations MUST NOT:

- skip validation
- bypass schema verification
- ignore metadata completeness
- assume exported JSON is valid
- report success before validation completes

Validation is mandatory.

---

# Acceptance Criteria

The Export Validation Layer is considered complete only if:

✓ Every export is validated.

✓ Metadata is complete.

✓ JSON is valid.

✓ Schema passes.

✓ Archive is readable.

✓ Message count matches.

✓ Images are verified.

✓ Attachments are verified.

✓ Validation reports are generated.

✓ False success is impossible.

---

# Definition of Done

The Export Validation Layer is production-ready only when every exported archive has been verified for correctness, completeness, integrity, schema compliance, metadata accuracy, and long-term usability before the export is reported as successful.

---

# Appendix A — Validation Decision Flow

```text
Conversation Ready
        │
        ▼
Metadata Validation
        │
        ▼
Message Validation
        │
        ▼
Content Validation
        │
        ▼
JSON Validation
        │
        ▼
Schema Validation
        │
        ▼
Integrity Validation
        │
        ▼
Archive Validation
        │
        ▼
PASS?
   │
   ├── YES ─────────► Export Success
   │
   └── NO
         │
         ▼
Generate Validation Report
         │
         ▼
Export Failed
```

---

# Appendix B — Mandatory Validation Checklist

Every export MUST pass all of the following checks:

| Validation Item             | Required |
| --------------------------- | -------- |
| Conversation Exists         | ✓        |
| Conversation ID             | ✓        |
| Title                       | ✓        |
| URL                         | ✓        |
| Metadata Complete           | ✓        |
| Messages Present            | ✓        |
| Message Count Verified      | ✓        |
| Message Order Preserved     | ✓        |
| Markdown Preserved          | ✓        |
| Code Blocks Preserved       | ✓        |
| Images Verified             | ✓        |
| Attachments Verified        | ✓        |
| JSON Valid                  | ✓        |
| Schema Valid                | ✓        |
| UTF-8 Encoding              | ✓        |
| Archive Readable            | ✓        |
| Integrity Verified          | ✓        |
| Validation Report Generated | ✓        |

---

End of Document
