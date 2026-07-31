# Requirements Traceability

This matrix connects public requirements to implementation, tests, and documentation.

## User workflow

| Requirement | Implementation | Tests or evidence | Documentation |
|---|---|---|---|
| Launch separate Chrome | browser manager profile resolution | browser launch tests | Quick start, Browser automation |
| Manual ChatGPT login | managed profile workflow | operational smoke test | Installation, Privacy |
| Scan conversations | sidebar scan | title and parser tests | Usage |
| Select and export | controller and task pipeline | export exclusivity tests | Usage |
| Manage archives | archive service | archive tests | Usage |

## Browser ownership and concurrency

| Requirement | Implementation | Tests or evidence | Documentation |
|---|---|---|---|
| One Playwright owner | browser session worker | worker serialization tests | Architecture |
| Composite export exclusivity | workflow gate | duplicate submission test | Browser automation |
| Lease release after failure or cancel | task done callback | exclusivity and task tests | Internal API |
| Expected cancellation | worker interruption path | cancellation log test | Troubleshooting |

## Readiness and large conversations

| Requirement | Implementation | Tests or evidence | Documentation |
|---|---|---|---|
| No zero-message completion | readiness policy | zero-message tests | Browser automation |
| One empty-shell recovery | reload policy | idle empty DOM tests | Troubleshooting |
| Progress can exceed stall interval | progress timestamps | 445-message test | Release notes |
| Stalled image bounded | image grace policy | stalled-image tests | Settings |
| Spinner separated from loader | observer state | spinner test | Browser automation |
| Semantic stability | message signature | image churn tests | Architecture |

## Message integrity

| Requirement | Implementation | Tests or evidence | Documentation |
|---|---|---|---|
| Checkpoint before scroll | checkpoint callback | incremental tests | Archive format |
| Atomic JSON | checkpoint store | round-trip tests | Archive format |
| Exact code bytes | byte writer and validator | CRLF test | Troubleshooting |
| Retry failed message | retry policy | reload and resume tests | Settings |
| Degraded placeholder | capture status | degraded tests | Usage |
| Timestamp provenance | parser and models | timestamp tests | Archive format |

## Asset handling

| Requirement | Implementation | Tests or evidence | Documentation |
|---|---|---|---|
| Explicit resource kind | pipeline and loader signature | routing regressions | Browser automation |
| Favicon filtering | parser | parser regressions | Release notes |
| Attachment fallback only for attachment | browser manager | asset routing tests | Troubleshooting |
| Authenticated retrieval | browser context | source review and smoke test | Known limitations |

## Titles and publication

| Requirement | Implementation | Tests or evidence | Documentation |
|---|---|---|---|
| Sidebar title canonical | controller and pipeline | title tests | Usage |
| Remove UI or project context | title normalization | sidebar tests | Browser automation |
| Stable collision suffix | archive builder | archive naming tests | Archive format |
| Atomic publish collision | publication loop | concurrent publish test | Release notes |
| Preserve old archive on failed overwrite | staging and replacement | rollback test | Usage |

## Windows filesystem

| Requirement | Implementation | Tests or evidence | Documentation |
|---|---|---|---|
| Short temporary names | byte writer and archive builder | short temp test | Release notes |
| Same-target JSON serialization | JSON writer | concurrency test | Architecture |
| Sharing-denial retry | JSON writer | Windows replace test | Troubleshooting |
| Safe filenames | sanitizer | security tests | Archive format |
| Root containment | path utilities | traversal tests | Security |

## Archive validation

| Requirement | Implementation | Tests or evidence | Documentation |
|---|---|---|---|
| Required paths | validator | archive tests | Archive format |
| Hash and size | validator | tamper tests | Release verification |
| Message links and counts | validator | regression tests | Archive format |
| Asset hashes | validator | asset tamper test | Archive format |
| RAG consistency | validator | RAG count test | Archive format |
| Warning and error distinction | validation model | degraded archive test | Usage |

## Configuration

| Requirement | Implementation | Tests or evidence | Documentation |
|---|---|---|---|
| Validated settings | Pydantic settings | config tests | Settings |
| Default retry count 5 | defaults, model, schema | repository tests | README |
| Worker values 1, 2, 4, 8 | validator | settings tests | Settings |
| Delay Auto, Fast, Normal, Safe | validator | settings tests | Settings |
| Memory Low, Balanced, High | validator | settings tests | Settings |
| Invalid recovery | config service | service test | Troubleshooting |

## Build and release

| Requirement | Implementation | Tests or evidence | Documentation |
|---|---|---|---|
| Windows source CI | `ci.yml` | Actions run | Release validation |
| Nuitka OneDir | build script and config | tag workflow | Release process |
| Verified ZIP | package script | ZIP test and checksum | Release verification |
| Automatic release assets | `release.yml` | tag run | Release process |
| Version consistency | release checklist | grep and manual review | Versioning |

## Public documentation boundary

Public requirements are defined by root README, changelog, support, security, contribution files, documentation under `docs/`, source and configuration, tests, and successful CI or release evidence.

No unavailable private document is required for public use or contribution.
