# Implementation Compliance

This document maps public architecture and product requirements to the v0.2.0 implementation.

## Platform and application

| Requirement | Implementation |
|---|---|
| Windows 10/11 x64 | Windows-targeted source and Nuitka OneDir workflow |
| Google Chrome Stable | Playwright Chrome channel and managed profile |
| Python 3.12 source runtime | `pyproject.toml`, CI, and lock files |
| Portable Windows package | Nuitka build plus release ZIP |
| No credential collection | Manual login inside Chrome |

## UI

| Requirement | Implementation |
|---|---|
| One desktop application | CustomTkinter composition root |
| Responsive UI | heavy work in managed tasks |
| Typed status and progress | queue and task events |
| Dashboard, Conversations, Archives, History, Settings, Logs, About | public pages |
| Safe shutdown | controller, task, and browser lifecycle |

## Browser automation

| Requirement | Implementation |
|---|---|
| One Playwright owner | `BrowserSessionWorker` |
| Managed persistent profile | `data/chrome-user-data` |
| Explicit CDP connect | separate Connect workflow |
| No automatic unrelated-CDP fallback | launch failure remains explicit |
| Sidebar scan | browser manager selectors and title extraction |
| Virtualized deep scan | observer plus accumulator |
| Progress-based stall | readiness policy |
| Empty-shell recovery | one bounded reload |
| Image grace | delay-mode policy |
| Exclusive composite workflow | controller workflow gate |

## Message integrity

| Requirement | Implementation |
|---|---|
| Preserve message order | source keys and sequence numbers |
| Checkpoint before scroll | checkpoint callback |
| Atomic message JSON | message checkpoint store |
| Exact code bytes | byte writes and read-back |
| Retry one failed message | configured retry count |
| Preserve previous progress | checkpoint resume |
| Explicit degraded message | capture status and warnings |
| Do not invent timestamps | provenance and nullable source time |

## Parsing and assets

| Requirement | Implementation |
|---|---|
| Text, Markdown, HTML | conversation parser |
| Code | code references and files |
| Images | explicit image resource routing |
| Decorative image filtering | favicon and interface source filter |
| Attachments | optional and resource-kind-specific |
| Tables | structured extraction |
| Citations | citation extraction and assets |
| Current message container | `data-message-id` fallback |

## Archive generation

| Requirement | Implementation |
|---|---|
| Frozen directory layout | archive builder |
| Deterministic JSON | model aliases and JSON writer |
| Human-readable Markdown | conversation document |
| RAG-ready data | RAG builder |
| Search, statistics, summary | generated documents |
| Staging | isolated archive build |
| Atomic publication | publish candidates and replacement |
| Collision-safe naming | title plus stable ID plus number |
| Short temp files | same-directory `.cv-*.tmp` |
| Validation before success | archive validator |

## Validation

| Requirement | Implementation |
|---|---|
| Required paths | validator |
| Schemas | JSON schema checks |
| Message links and order | recomputation |
| Character and count consistency | recomputation |
| Asset path safety | root containment |
| Asset hashes and sizes | SHA-256 and bytes |
| RAG consistency | chunk and map checks |
| Code bytes | exact UTF-8 comparison |
| Warnings distinct from errors | validation result model |

## Persistence

| Requirement | Implementation |
|---|---|
| Validated settings | Pydantic models |
| Atomic settings and history | JSON writer |
| Invalid recovery | invalid-file preservation |
| Transient Windows retry | bounded replace retry |
| Same-target serialization | write guard |

## Security

| Requirement | Implementation |
|---|---|
| Path traversal rejection | safe path utilities |
| Windows-safe names | sanitization |
| Safe archive deletion | direct-child restriction |
| No committed Chrome profile | `.gitignore` |
| No public runtime logs or exports | `.gitignore` |
| No image-to-attachment fallback | explicit resource kind |
| No silent validation bypass | errors remain fatal |

## Documentation

The public documentation covers installation, beginner quick start, usage, settings, archive format, browser behavior, troubleshooting, FAQ, privacy, limitations, upgrade, checksum verification, release process, security, and contribution.

## Automated evidence

The Windows source CI passed 81 tests for the reviewed v0.2.0 source commit.

The final portable release remains conditional on the successful tag-triggered Nuitka workflow and a clean smoke test.
