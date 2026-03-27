## Post-Critique Changes

- Identified repetitive parser-registration boilerplate across the `gcloud` command tree. The first version repeated the same `add_parser(...); set_defaults(...)` pattern for every command node, which would make later CLI tickets noisier than necessary.
- Extracted `_add_help_parser(...)` to centralize the parser-plus-help-handler pattern and keep later command additions focused on command-specific arguments and handlers.
- While broadening parser verification, also fixed an adjacent root-entrypoint inconsistency in `harnessiq.cli.main`: the existing `research-sweep` command family was present in the repo but was never registered at the top level. That omission was corrected because this ticket already touched the same entrypoint and the broader parser suite would remain red otherwise.
- Re-ran the parser verification sweep after the refinement:
  - `pytest tests/test_gcloud_cli.py tests/test_model_profiles.py tests/test_ledger_cli.py tests/test_research_sweep_cli.py`
- Result after refinement: the full parser sweep passed.
