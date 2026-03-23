## Ticket 2 Quality Results

Verification run:

```text
python -m pytest tests/test_harness_manifests.py tests/test_exa_outreach_cli.py tests/test_leads_cli.py tests/test_instagram_cli.py tests/test_linkedin_cli.py tests/test_prospecting_cli.py tests/test_sdk_package.py
```

Observed results:

- `tests/test_harness_manifests.py`: passed
- `tests/test_exa_outreach_cli.py`: passed
- `tests/test_leads_cli.py`: passed
- `tests/test_instagram_cli.py`: passed
- `tests/test_linkedin_cli.py`: passed
- `tests/test_prospecting_cli.py`: passed
- `tests/test_sdk_package.py`: only the pre-existing unrelated provider-structure failure remains

Additional fixes validated during this run:

- sink connection lookup is now lazy when no explicit sink specs are passed
- HarnessIQ home-directory resolution now falls back cleanly when `Path.home()` cannot be resolved under a stripped environment
