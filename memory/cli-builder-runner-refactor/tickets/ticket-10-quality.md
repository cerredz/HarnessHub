Stage 1 - Static Analysis
- No dedicated linter is configured for this CLI package. I manually reviewed the new assertions to confirm they target command contracts and shared helper behavior rather than private implementation details.

Stage 2 - Type Checking
- No project type checker is configured for this repository. The updated regression suite files passed Python bytecode compilation.
- Command: `python -m compileall tests/test_cli_common.py tests/test_platform_cli.py tests/test_linkedin_cli.py tests/test_instagram_cli.py tests/test_leads_cli.py tests/test_prospecting_cli.py tests/test_exa_outreach_cli.py tests/test_research_sweep_cli.py tests/test_cli_builders.py tests/test_cli_runners.py`

Stage 3 - Unit Tests
- Command: `pytest tests/test_cli_common.py tests/test_platform_cli.py tests/test_linkedin_cli.py tests/test_instagram_cli.py tests/test_leads_cli.py tests/test_prospecting_cli.py tests/test_exa_outreach_cli.py tests/test_research_sweep_cli.py tests/test_cli_builders.py tests/test_cli_runners.py`
- Result: `131 passed`

Stage 4 - Integration & Contract Tests
- The targeted CLI suite now covers the shared helper layer, the platform manifest path, and every migrated legacy CLI family. New coverage specifically locks the `outreach --search-only` contract and the Research Sweep missing-Serper error path.
- Command: `pytest tests/test_cli_common.py tests/test_platform_cli.py tests/test_linkedin_cli.py tests/test_instagram_cli.py tests/test_leads_cli.py tests/test_prospecting_cli.py tests/test_exa_outreach_cli.py tests/test_research_sweep_cli.py tests/test_cli_builders.py tests/test_cli_runners.py`
- Result: `131 passed`

Stage 5 - Smoke & Manual Verification
- Executed focused in-process smoke checks for the new regression targets:
  - `outreach run --agent a --memory-root <temp> --model-factory mod:model --exa-credentials-factory mod:exa --search-only`
  - `research-sweep run --agent sweep-a --memory-root <temp> --model-factory mod:model`
- Observed the `outreach --search-only` path completed without Resend/email-template factories and confirmed the Research Sweep run raised the expected missing-Serper credential error when no factory or bound credentials were present.
