## Self-Critique Findings

### Improvement 1 - Expose instance-storage passthroughs on the shared scaffold

- Initial implementation did not pass `memory_path`, `repo_root`, or `instance_name` through to `BaseAgent`.
- Consequence: the new unit tests instantiated the scaffold against the repository root and polluted tracked `memory/agent_instances.json`.
- Fix applied:
  - added `memory_path`, `repo_root`, and `instance_name` passthrough parameters to `BaseProviderToolAgent.__init__`
  - updated `tests/test_provider_base_agents.py` to use `TemporaryDirectory()` as an isolated repo root
- Why this is better:
  - keeps the shared scaffold aligned with `BaseAgent`'s instance-storage controls
  - makes future provider-specific harnesses easier to test and embed in isolated environments
  - prevents the new test suite from depending on or mutating repository-local runtime state

## Post-Critique Verification

- Re-ran `python -m unittest tests.test_provider_base_agents tests.test_email_agent tests.test_agents_base`
- Re-ran the manual smoke snippet with a temporary repo root
- Both checks passed after the refinement
