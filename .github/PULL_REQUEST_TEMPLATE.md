## Summary

Describe the problem and the exact change.

## User impact

Explain what users will notice. State whether archive output, browser behavior, settings, or upgrade behavior changes.

## Root cause

For a bug fix, explain the verified root cause. Avoid assumptions.

## Implementation

Describe the affected modules and data flow.

## Compatibility

- Backward compatibility:
- Archive schema impact:
- Settings migration impact:
- Windows/Nuitka impact:

## Verification

List the commands and operational tests performed.

```text
python scripts/test/check_environment.py --skip-chrome
python scripts/test/run_tests.py
python -m compileall -q src tests
git diff --check
```

## Security and privacy

Describe path handling, browser-session data, logs, credentials, and untrusted input considerations.

## Performance and concurrency

Describe UI-thread safety, browser-worker ownership, memory, timing, and race-condition considerations.

## Documentation

List every updated public document.

## Checklist

- [ ] The change is focused and complete.
- [ ] Existing behavior is preserved unless an approved change is documented.
- [ ] Playwright objects remain on the dedicated browser worker.
- [ ] Archive validation and safe path controls are not weakened.
- [ ] New or changed behavior has regression tests.
- [ ] Local verification passed.
- [ ] Documentation is updated.
- [ ] No personal runtime data, Chrome profile, exports, logs, secrets, or temporary files are included.
- [ ] Version metadata is synchronized when this is a release change.
- [ ] I reviewed [Architecture](../docs/developer/architecture.md).
- [ ] I reviewed [Contributing](../CONTRIBUTING.md).
- [ ] I reviewed [Security](../SECURITY.md).
