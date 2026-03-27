## Summary

- add the new bundled `orchestrator_master_prompt` asset to the master prompt catalog
- extend `tests/test_master_prompts.py` for the new prompt key and its `Identity / Persona` structure
- preserve the exact prompt body in `memory/add-orchestrator-master-prompt/source_prompt.md` for fidelity verification

## Verification

- `python -m pytest tests/test_master_prompts.py tests/test_master_prompts_cli.py tests/test_master_prompt_session_injection.py`
- direct `get_prompt("orchestrator_master_prompt")` round-trip check returned `MATCH` against `memory/add-orchestrator-master-prompt/source_prompt.md`

## Issue

- Closes #348
