# Implementation Compliance

## Architecture traceability

| Frozen layer | Implementation | Status |
|---|---|---|
| CustomTkinter UI | `src/ui/` | PASS |
| Controller boundary | `src/controllers/application_controller.py` | PASS |
| Managed task queue | `src/core/task_manager.py` | PASS |
| Dedicated Playwright lane | `src/browser/session_worker.py` | PASS |
| Browser integration | `src/browser/browser_manager.py` | PASS |
| Parsing and models | `src/parsers/`, `src/models/` | PASS |
| Archive/RAG services | `src/core/archive_builder.py`, `rag_builder.py` | PASS |
| Validation and management | `src/core/archive_validator.py`, `src/services/archive_repository.py` | PASS |
| Build and release source configuration | `nuitka.toml`, `scripts/build/`, `.github/workflows/` | PASS |
| Windows OneDir compile/runtime proof | official Windows CI + clean-machine validation | FAIL — not executable in this Linux audit environment |
| Exact frozen runtime-only binary layout | compiled OneDir inspection | FAIL — standard Nuitka root dependencies may conflict with the frozen layout |

## Invariants

- UI thread performs presentation and event polling only.
- Playwright objects never cross the browser worker boundary.
- Browser exports are serialized.
- Output is written atomically through a staging directory.
- External paths and archive-relative references are validated.
- Existing frozen dependencies and public architecture are preserved.
- Out-of-scope cloud sync, SQLite, embeddings, semantic search, plugins, and archive viewer are not introduced.
