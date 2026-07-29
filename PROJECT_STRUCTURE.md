# ContextVault Project Structure

The repository uses the frozen responsibility-based architecture below. Folder and module names are public project structure and must not be renamed without an approved specification change.

```text
.
├── .github/
│   ├── workflows/ci.yml
│   └── workflows/release.yml
├── assets/
│   ├── icons/
│   ├── images/
│   └── themes/
├── config/
│   ├── defaults.json
│   └── schemas/
├── data/
│   └── templates/
├── docs/
│   ├── api/
│   ├── configuration/
│   ├── developer/
│   ├── faq/
│   ├── features/
│   ├── getting-started/
│   ├── guides/
│   ├── release-notes/
│   └── troubleshooting/
├── examples/
├── project/
├── scripts/
│   ├── build/
│   ├── release/
│   └── test/
├── src/
│   ├── app/
│   ├── browser/
│   ├── config/
│   ├── controllers/
│   ├── core/
│   ├── models/
│   ├── parsers/
│   ├── services/
│   ├── ui/
│   └── utils/
├── tests/
│   └── fixtures/
├── CHANGELOG.md
├── LICENSE
├── README.md
├── README.txt
├── nuitka.toml
├── pyproject.toml
├── requirements.txt
├── requirements.lock
├── requirements-build.lock
├── run.bat
└── vibproject.ygit
```

## Responsibility rules

- `src/ui/` contains presentation only and never imports browser implementation modules.
- `src/controllers/` is the public UI workflow boundary.
- `src/core/` owns managed tasks and archive/export business logic.
- `src/browser/` owns all Playwright and Chrome interaction.
- `src/parsers/` transforms fully loaded HTML into validated domain records.
- `src/models/` defines internal and external contracts.
- `src/services/` owns persistent settings, history, logging, and archive management.
- `src/utils/` contains shared deterministic helpers without business workflows.
- `project/` contains frozen engineering specifications and remains the source of truth.
- Generated runtime data, builds, exports, logs, and release artifacts are excluded from version control.
