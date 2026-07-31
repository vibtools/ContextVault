# Forensic Audit Report — v0.2.0 Export Reliability

**Audit scope:** export failures reported during large, image-heavy, and repeated conversation exports
**Application target:** 0.2.0
**Archive schema:** 1.0
**Public source commit reviewed before documentation preparation:** `dab5d0bc5f0c5e9ae1028722ed1a364be15615cb`

## Executive summary

The reported failures were not one isolated timeout. They were a chain of independent defects exposed at different export stages.

The v0.2.0 source addresses:

- fixed total readiness timeout;
- missing incremental checkpoint wiring;
- stale zero-message completion;
- permanently pending browser images;
- broad loading-selector coupling;
- decorative favicon extraction;
- incorrect asset fallback routing;
- duplicate export interleaving;
- title source selection;
- archive publication race;
- Windows temporary path length;
- misleading cancellation logging.

## Incident 1: fixed 900-second readiness exhaustion

### Symptom

A large conversation continued producing meaningful progress but failed when a 900-second total readiness budget expired.

### Root cause

Both browser loading and export orchestration applied absolute deadlines. Incremental checkpoint components existed but were not fully connected to the deep-scan workflow.

### Correction

- replaced total elapsed deadline with meaningful-progress stall detection;
- wired checkpoint callback and verification;
- removed the second outer absolute timeout;
- preserved checkpointed messages across recovery;
- added large-conversation regression coverage.

## Incident 2: favicon routed as an attachment

### Symptom

During image collection, an HTTP 404 for a decorative favicon caused ContextVault to search the page for an attachment control for up to 180 seconds.

### Root cause

- every message image element was treated as exportable;
- resource kind was not propagated through all loader boundaries;
- image HTTP errors used attachment fallback;
- attachment fallback reset and scanned the page.

### Correction

- filter known decorative favicon and interface sources;
- propagate explicit resource kind;
- permit attachment UI fallback only for attachments;
- preserve compatibility where required;
- add routing regression tests.

## Incident 3: duplicate exports and archive collision

### Symptom

Two exports of the same conversation started almost simultaneously. One captured fewer messages and published first. The fuller export later failed because the target already existed.

### Root cause

- low-level browser commands were serialized, but the composite export workflow was not;
- title came from message-page headings instead of canonical sidebar metadata;
- target existence was checked before a long build;
- final publication had a time-of-check/time-of-use race.

### Correction

- add exclusive browser workflow lease;
- reject duplicate submissions before browser interleaving;
- use scanned sidebar title;
- use stable conversation-ID suffix;
- resolve final target atomically at publication;
- release the lease through task completion callbacks.

## Incident 4: stalled image prevented any scroll

### Symptom

The application reached message stabilization but did not scroll. Restarting reproduced the same state.

### Root cause

- a terminal broken image was treated as pending forever;
- readiness directly required pending image count zero;
- pending counts were retained across virtualized windows;
- broad loading selectors counted image spinners as blocking loaders;
- spinner mutations reset stabilization;
- progress labels did not identify the image wait clearly.

### Correction

- only incomplete images remain browser-pending;
- separate image and blocking loaders;
- track image wait by message key and count;
- apply bounded grace by delay mode;
- accept stalled image state with warning;
- preserve semantic stabilization;
- propagate warning into archive metadata and logs.

## Incident 5: Windows path and temporary files

### Symptom

Asset writes failed with `FileNotFoundError` when temporary filenames extended already long Windows paths.

### Root cause

Temporary filenames repeated the complete target filename plus a UUID suffix.

### Correction

Use short same-directory temporary names such as `.cv-*.tmp`.

## Incident 6: cancellation reported as failure

### Symptom

User cancellation produced an ERROR traceback that looked like a browser defect.

### Root cause

The worker logged expected interruption through the generic exception path.

### Correction

Expected interruption is logged at information level as browser command cancellation. Unexpected exceptions remain errors.

## Validation evidence

GitHub Actions Windows Python 3.12 source CI completed successfully for the reviewed commit.

The source suite passed 81 tests, including:

- archive build and validation;
- concurrent publication;
- overwrite rollback;
- short temporary paths;
- managed profile resolution;
- title normalization;
- browser-worker cancellation and restart;
- export exclusivity;
- 445-message progress beyond timeout;
- checkpoint reload and resume;
- degraded-message behavior;
- exact CRLF code bytes;
- image-spinner and stalled-image readiness;
- zero-message recovery;
- parser compatibility;
- repository integrity;
- security path handling;
- atomic JSON replacement;
- task callbacks and cancellation.

## Evidence limitations

The source CI does not compile the final Nuitka release.

The tag-triggered Build and Release workflow remains authoritative for MSVC/Nuitka success, OneDir completeness, packaged ZIP integrity, checksum generation, and GitHub Release assets.

A real authenticated Windows and Chrome smoke export should be performed before treating the release as operationally complete.

## Final audit status

| Area | Result |
|---|---|
| Root causes identified | PASS |
| Source corrections present | PASS |
| Automated Windows source CI | PASS |
| 81-test forensic suite | PASS |
| Public documentation corrected | Prepared for commit |
| Tag-triggered Nuitka build | Pending release tag |
| Clean portable smoke test | Required before final sign-off |
