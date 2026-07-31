# Forensic Audit Report

**Project:** ContextVault  
**Version:** 1.0.0  
**Audit date:** 2026-07-28  
**Source:** uploaded `ContextVault.zip`; GitHub repository `vibtools/ContextVault` was empty at audit time.

## 1. Discovery baseline

The uploaded archive contained 59 original files and 103 ZIP entries. All 59 original files remain present at their original paths. The initial repository supplied complete frozen engineering specifications but almost no application implementation: source packages and tests were empty, launch/build/test scripts were placeholders, two test scripts were syntactically invalid, user documentation and GitHub workflows were absent, and `nuitka.toml` was Markdown-wrapped rather than valid TOML.

## 2. Architecture assessment

The implemented system preserves the frozen architecture exactly:

```text
CustomTkinter UI
    -> ApplicationController
    -> TaskManager / ThreadPoolExecutor / queue.Queue
    -> BrowserSessionWorker / asyncio event loop
    -> Playwright / official Google Chrome
    -> BeautifulSoup + Markdownify parser / Pydantic models
    -> ArchiveBuilder / RagBuilder / ArchiveValidator
```

No alternate UI framework, browser engine, database, cloud service, embeddings system, plugin framework, or unauthorized runtime dependency was introduced.

## 3. Initial critical findings and disposition

| Finding | Severity | Disposition |
|---|---:|---|
| Empty application packages and tests | Critical | Implemented complete frozen source architecture and regression suite. |
| Placeholder/invalid launcher and test scripts | Critical | Replaced with executable environment, test, build, maintenance, and release scripts. |
| Invalid `nuitka.toml` and missing build resources | Critical | Added valid TOML, icon/resources, locked build tooling, Windows workflow, and packager. |
| Missing configuration, schemas, templates, workflows, and docs | High | Added validated defaults, generated schemas, resources, CI/release automation, and synchronized documentation. |
| Shared atomic JSON temporary filename race | High | Replaced with unique same-directory temporary files, flush/fsync, and atomic `os.replace`; concurrency regression test added. |
| Archive overwrite could risk previous output | High | Added staging publication, backup/rollback, atomic ZIP replacement, and regression tests. |
| Message content deduplication could discard legitimate repeated messages | High | Deduplication now uses only stable source message IDs; repeated-content regression test added. |
| Chrome profile name accepted platform-specific separators | High | Rejects absolute paths, traversal, NUL, `/`, and `\` on every platform; security test added. |
| Launch Chrome used the regular Chrome `User Data` root | Critical | Blank/default regular roots now resolve to ContextVault-owned `data/chrome-user-data`; automatic CDP fallback was removed; six regression tests and a headed Chromium smoke test verify the corrected launch contract. |
| Validator trusted stored counts/reference metadata | High | Recomputes message links/counts, code/table payloads, asset size/hash, mappings, RAG counts, and keyword consistency. |
| Browser worker start/stop race and non-propagated cancellation | High | Added lock-protected lifecycle, active asyncio cancellation, queued-future draining, restart safety, and concurrency tests. |
| Sidebar scan captured only current DOM | High | Added cancellation-aware scroll-to-stable scanning that accumulates virtualized/lazy-loaded links. |
| Conversation loader could choose sidebar as largest scroller | High | Selects the closest scrollable ancestor of message nodes before fallback. |
| Missing browser retry strategy | Medium | Added bounded exponential retries for transient scan/navigation/load/download/reload failures. |
| `TaskManager.shutdown(timeout)` ignored timeout | Medium | Added bounded future wait, cancellation, and warning for unfinished tasks. |
| Windows drop callback pointer types could truncate on x64 | Medium | Added pointer-width-safe ctypes prototypes and callback pointer conversion. |
| PIL icon file handle remained open | Low | Image is copied inside a context manager before creating the CustomTkinter image. |

## 4. Verification performed

- Full source AST and bytecode compilation.
- 55 standard-library regression tests: isolated browser-profile resolution, explicit CDP behavior, parser, archive, validator, rollback, atomic writes, security, services, task manager, browser worker, configuration, dependency synchronization, and architecture boundaries.
- JSON/TOML parsing and schema/resource presence checks.
- Original-file preservation comparison.
- Hygiene scans for merge markers, unfinished implementation markers, wildcard imports, bare exceptions, debug calls, and credential-like content.
- Release packager exercised against a synthetic OneDir fixture; ZIP CRC, required members, and SHA-256 checksum passed.
- Linux environment gate executed; Windows-only build command correctly refused the unsupported platform.

## 5. Remaining release risks

No known critical source defect remains. The following mandatory validation is external and therefore still open:

1. Install the exact locked runtime/build dependencies on Windows x64.
2. Execute the official MSVC/Nuitka build and inspect compiler warnings.
3. Confirm the complete compiled dependency/DLL layout.
4. Launch the EXE and all UI pages on clean Windows 10 and Windows 11 machines.
5. Run exports using a real authenticated Chrome Stable profile, including extensions and CDP.
6. Measure startup, browser startup, memory, CPU, and large-conversation export behavior.
7. Run GitHub Actions and inspect/upload the actual release artifact.
8. Resolve or formally amend the frozen requirement that no runtime binary may exist beside the EXE: standard Nuitka OneDir commonly requires compiled dependencies at the distribution root, so this exact layout cannot be certified from source configuration alone.

## 6. Audit conclusion

The repository is a complete, internally validated **source release candidate**. It is **not certified as a stable portable Windows release** until the FAIL gates in `release-validation.md` pass.

## 7. Incremental message-integrity re-audit — 2026-07-30

A production export of 272 messages completed browser deep scanning but failed final validation with repeated `Code reference ... file content does not match rawCode` errors. The re-audit traced the error to newline handling rather than failed collection: code bytes were written losslessly, while the validator used `Path.read_text()`, whose universal-newline behavior converted CRLF to LF on read. Exact-byte comparison now preserves both CRLF and LF code blocks.

The same re-audit identified a reliability limitation in end-of-conversation-only validation. The browser worker now commits each settled virtualized message window through `MessageCheckpointStore` before scrolling. Message JSON is atomically round-tripped, code files are byte-verified, failed keys are retried, at most one page reload per failed key resumes from retained checkpoints, and an exhausted content fragment becomes an explicit degraded placeholder rather than aborting the complete conversation. Fatal infrastructure/storage/browser failures are not masked.

Timestamp fields are additive and provenance-aware: reliable source message timestamps drive conversation start/end; unavailable source timestamps remain null/unknown; capture and export timestamps are labeled separately. The frozen final archive folder layout and public controller/browser commands remain unchanged.

Verification evidence now includes 53 passing tests, including a 272-message archive with 90 CRLF code blocks, degraded-message publication with warnings, exact-byte code validation, settings persistence, page reload/resume, and exhausted-message continuation.
