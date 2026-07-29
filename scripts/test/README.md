# Test Utilities

- `python scripts/test/checkmodules.py` checks every frozen runtime package and exact locked version.
- `python scripts/test/check_environment.py` checks Python, required files, TOML/JSON configuration, modules, and Google Chrome.
- `python scripts/test/check_environment.py --skip-chrome` is suitable for non-Windows source CI.
- `python scripts/test/run_tests.py` compiles source/scripts/tests and runs the complete standard-library `unittest` suite.
- `run_tests.bat` and `run_pytest.bat` are Windows-compatible wrappers. The latter filename is retained for compatibility; it does not introduce pytest.
