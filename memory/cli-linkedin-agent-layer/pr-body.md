## Summary

- add a package-native `harnessiq` CLI with a LinkedIn command group
- add managed per-agent LinkedIn memory for runtime params, custom params, prompt data, and copied files
- document and test the new CLI workflow, including wheel/package smoke coverage

## Details

- `harnessiq linkedin prepare|configure|show|run` now provides a scriptable CLI surface for the LinkedIn SDK flow
- imported files are copied into managed agent memory storage and recorded with source-path metadata
- `LinkedInJobApplierAgent` can now be constructed from persisted memory-backed runtime parameters via `from_memory(...)`
- package metadata now exposes the `harnessiq` console script

## Verification

- `python -m unittest`
- `python -m harnessiq.cli --help`
- `python -m harnessiq.cli linkedin configure --agent smoke-agent --memory-root <temp> ...`
- `python -m harnessiq.cli linkedin run --agent smoke-agent --memory-root <temp> --model-factory tests.test_linkedin_cli:create_static_model --max-cycles 1`
