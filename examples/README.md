# Examples

`tests/fixtures/sample_conversation.html` is the canonical deterministic parser and archive-generation fixture. Run `python -m unittest tests.test_archive -v` to generate and validate a complete temporary archive without committing runtime output.

Generated user archives are intentionally excluded from version control because they may contain private conversation content and downloaded attachments.
