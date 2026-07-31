# Test Utilities

## Recommended release-candidate verification

Run this from the repository root:

```powershell
python scripts/release/verify_release_candidate.py --ref main --skip-chrome
```

This creates or repairs an isolated `.venv-release` environment, installs the exact versions from `requirements.lock`, verifies release metadata, runs the full source/environment audit, executes the test suite, compiles Python files, and checks staged and unstaged diffs.

Use `--reset` when the isolated environment must be recreated. Add `--include-build-dependencies` when local Nuitka tooling is also required.

The script does not modify the user's global Python environment.

## Individual utilities

- `python scripts/test/checkmodules.py` checks every frozen runtime package and exact locked version in the active Python interpreter.
- `python scripts/test/check_environment.py` checks Python, required files, TOML/JSON configuration, modules, and Google Chrome.
- `python scripts/test/check_environment.py --skip-chrome` is suitable for source-only CI or documentation/release preparation.
- `python scripts/test/run_tests.py` compiles source/scripts/tests and runs the complete standard-library `unittest` suite.
- `run_tests.bat` and `run_pytest.bat` are Windows-compatible wrappers. The latter filename is retained for compatibility; it does not introduce pytest.

## Interpreting output

Some regression tests intentionally create invalid archives or simulated task failures. Their diagnostic log lines may contain words such as `failed`, `error`, or `RuntimeError`. They are not suite failures when the test line ends with `ok` and the final summary is:

```text
Ran 81 tests

OK
```

A real failure appears as `FAIL`, `ERROR`, a non-zero command exit, or a final suite summary that is not `OK`.

## Public repository boundary

Before staging or releasing, run:

```powershell
python scripts/release/verify_public_tree.py
```

This read-only check prevents private maintainer specifications, isolated environments, browser profile data, runtime state, logs, exports, builds, and artifacts from entering the public Git index.
