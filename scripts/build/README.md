# Windows build orchestration

`build_windows.py` is the official translation boundary between `nuitka.toml` and the Nuitka CLI used by GitHub Actions and local Windows release builds.

It performs these deterministic steps:

1. validates the checked-in TOML schema and all referenced source/data paths;
2. verifies Windows, Python 3.12, and the exact locked Nuitka version;
3. removes stale ignored build output;
4. compiles the configured standalone OneDir distribution with MSVC;
5. locates exactly one `.dist` directory containing `ContextVault.exe`;
6. creates the portable writable `data`, `exports`, and `logs` directories;
7. verifies every path required by `package_release.py`;
8. writes `build/distribution-path.txt` for deterministic packaging.

Run only from the repository root after installing `requirements.lock` and `requirements-build.lock`:

```powershell
python scripts/build/build_windows.py
```

The build script never reads or packages the private `project/` directory, local Chrome profile, settings, export history, existing exports, or logs.

## Repository tracking contract

The root generated-output directories are ignored with anchored rules (`/build/`, `/dist/`, and `/artifacts/`). The `scripts/build/` directory remains normal source code, while Python bytecode under `__pycache__/` remains ignored.
