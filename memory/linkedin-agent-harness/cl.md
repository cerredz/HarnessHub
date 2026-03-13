## Summary

- add a new `src/agents/` package with a provider-agnostic base agent runtime
- implement `LinkedInJobApplierAgent` with durable memory files, prompt assembly, pause handling, and LinkedIn-specific harness tools
- add unit coverage for the generic agent loop and the LinkedIn harness
- update the repository file index to record the new agent package and tests

## Notes

- the PR branch removes an accidental dependency from `src/agents/base.py` on unrelated local context-compaction work so the LinkedIn harness ships as a self-contained change
- the rolling transcript now stores assistant turns, tool calls, and tool results as separate entries, matching the LinkedIn harness specification

## Verification

- `python -m unittest tests.test_agents_base tests.test_linkedin_agent`
- `python -m unittest`
- smoke script: instantiate `LinkedInJobApplierAgent` with a fake model and confirm `action_log.jsonl` is written in a temporary memory directory
