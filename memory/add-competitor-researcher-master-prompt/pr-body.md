## Summary

- add the bundled `competitor_researcher` master prompt to the prompt catalog
- extend master-prompt regression coverage for the new bundled key
- sync generated repo docs after the prompt catalog changed

## Verification

- `pytest tests/test_master_prompts.py tests/test_master_prompts_cli.py tests/test_master_prompt_session_injection.py tests/test_docs_sync.py`
- `python scripts/sync_repo_docs.py --check`
