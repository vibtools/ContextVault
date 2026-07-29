# 📄 ContextVault — JSON Schema Standard

> **Version:** 1.0 (Frozen)

This document defines the official JSON schema standards for the ContextVault project.

Every JSON document generated, stored, exported, or consumed by the project must follow these standards.

This includes:

* Archive Metadata
* Conversation Data
* Manifest Files
* Configuration Files
* Statistics
* Project Metadata
* `vibproject.ygit`
* Future JSON-based formats

These rules apply equally to human developers and AI-generated code.

---

# 🎯 Primary Objectives

Every JSON document must be

* Consistent
* Predictable
* Human Readable
* Machine Readable
* Backward Compatible
* Forward Extensible
* Versioned
* Deterministic

---

# Core Principles

All JSON structures should follow these principles:

* Explicit over implicit
* Stable key naming
* Strong typing
* Schema validation
* Version awareness
* No duplicated information
* Predictable ordering
* Portable across operating systems

---

# Official Encoding

All JSON files must use

```text id="5y5u5m"
UTF-8
```

without BOM.

---

# Indentation

Official formatting

```text id="97qaj2"
4 spaces
```

Tabs are prohibited.

---

# Line Endings

Use standard UTF-8 text files.

Repositories should normalize line endings through Git configuration.

---

# Root Object Rule

Every JSON document must begin with a root object.

Correct

```json id="0djlwm"
{
    "schemaVersion": "1.0",
    "metadata": {},
    "data": {}
}
```

Avoid root arrays unless the format explicitly requires one.

---

# Required Metadata

Every exported JSON document should contain metadata similar to:

```json id="yieexv"
{
    "schemaVersion": "1.0",
    "format": "contextvault",
    "generatedBy": "ContextVault",
    "generatedAt": "...",
    "version": "...",
    "data": {}
}
```

This allows future compatibility and validation.

---

# Schema Versioning

Every schema must include

```text id="vljlwm"
schemaVersion
```

Example

```json id="bbdmtm"
{
    "schemaVersion": "1.0"
}
```

Schema versions must follow semantic versioning where practical.

---

# Application Version

Generated documents should include

```text id="wdlwba"
version
```

representing the application version that created the file.

---

# Timestamp Format

Use

```text id="39k92o"
ISO-8601
```

Example

```text id="clpw4s"
2026-07-28T15:42:17Z
```

Do not use locale-specific date formats.

---

# Naming Convention

All JSON keys must use

```text id="3pgs39"
camelCase
```

Examples

```json id="ewod0o"
conversationCount

archiveName

browserProfile

exportSettings

createdAt

updatedAt

imageCount
```

Avoid

```json id="r3zvba"
Conversation_Count

Archive_Name

browser_profile

Created_Date
```

---

# Key Ordering

Use consistent ordering.

Recommended order

```text id="0imjlwm"
schemaVersion

format

version

metadata

settings

statistics

data
```

Ordering should remain stable between exports.

---

# Data Types

Use appropriate JSON types.

* String
* Number
* Boolean
* Array
* Object
* null (only when appropriate)

Never store numbers as strings unless required by the specification.

---

# Null Usage

Avoid unnecessary null values.

Preferred

```json id="qgxfem"
{
    "images": []
}
```

instead of

```json id="vrwe0l"
{
    "images": null
}
```

unless null has semantic meaning.

---

# Arrays

Arrays should contain objects of the same type.

Example

```json id="r9s0a8"
[
    {
        "id": "...",
        "title": "..."
    },
    {
        "id": "...",
        "title": "..."
    }
]
```

Avoid mixed-type arrays.

---

# Object Structure

Related fields should be grouped logically.

Example

```json id="2a7oig"
{
    "metadata": {},
    "statistics": {},
    "conversations": []
}
```

Avoid deeply nested objects without clear purpose.

---

# Configuration Files

Configuration JSON should contain only configurable values.

Do not store runtime state inside configuration files.

---

# Runtime State

Temporary runtime information should not be written into permanent JSON files unless explicitly required.

Examples

* Current progress
* Active thread ID
* Temporary browser state

---

# Validation

Every JSON document should be validated before use.

Validation should verify

* Required fields
* Data types
* Version compatibility
* Structural integrity

Reject malformed JSON immediately.

---

# Unknown Fields

Consumers should ignore unknown fields when safe.

This improves forward compatibility.

---

# Required Fields

Required fields must never be omitted.

Optional fields should be documented.

---

# Identifiers

Every persistent object should have a stable identifier.

Preferred

```text id="ibjlwm"
UUID
```

or another deterministic unique identifier defined by the specification.

---

# File References

Use relative paths whenever possible.

Avoid absolute paths.

Correct

```text id="8swdj0"
assets/logo.png
```

Avoid

```text id="9nd1pi"
C:\Users\User\Desktop\logo.png
```

---

# Numbers

Use numeric values for

* Counts
* Sizes
* Durations
* Versions (when numeric)

Avoid formatting numbers as strings.

---

# Booleans

Use proper boolean values.

Correct

```json id="2g8fr9"
{
    "isArchived": true
}
```

Avoid

```json id="v6n1oa"
{
    "isArchived": "yes"
}
```

---

# Security Rules

Never store

* Passwords
* API Keys
* Access Tokens
* Session Cookies
* Secrets

in exported JSON files.

Sensitive information must be excluded or safely protected according to the project specification.

---

# Pretty Printing

Exported JSON should be human-readable.

Use consistent indentation.

Do not minify project-generated JSON unless explicitly required.

---

# Comments

JSON comments are not allowed.

Do not include

```text id="htrv2d"
//
/*
*/
```

inside JSON documents.

---

# Compatibility

Every schema change should consider

* Backward compatibility
* Forward compatibility
* Migration strategy

Breaking schema changes require a new schema version.

---

# vibproject.ygit

The project manifest must comply with this standard.

It should include

* schemaVersion
* metadata
* project
* technology
* runtime
* build
* release
* branding
* licensing

and any future approved sections.

---

# AI Requirements

AI-generated JSON must

* follow the approved schema,
* use correct data types,
* preserve key ordering,
* include required metadata,
* include schemaVersion,
* remain valid JSON,
* remain compatible with existing project tooling.

AI must never invent undocumented schema fields without explicit approval.

---

# Validation Checklist

Before accepting any JSON document verify:

* Valid UTF-8 encoding
* Valid JSON syntax
* Correct schemaVersion
* Required fields present
* Correct data types
* Consistent key naming
* Stable key ordering
* No duplicate keys
* No absolute paths
* No secrets
* Schema compatibility maintained

---

# Forbidden Practices

Never:

* Generate invalid JSON.
* Omit required metadata.
* Change key names without updating the schema version.
* Store sensitive information.
* Use inconsistent naming conventions.
* Mix unrelated data in the same object.
* Introduce undocumented fields into frozen schemas.
* Break backward compatibility without an approved migration strategy.

---

# Final Standard

Every JSON document produced by ContextVault must be deterministic, versioned, validated, portable, and compatible with the official project specifications.

A JSON file is considered production-ready only when it:

* passes schema validation,
* follows the official naming and formatting rules,
* preserves compatibility,
* and can be reliably processed by both current and future versions of ContextVault.
