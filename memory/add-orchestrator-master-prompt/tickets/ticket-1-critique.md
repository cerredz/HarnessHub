Self-critique findings:

- Persona-style prompt section requirements were duplicated conceptually before this change.

Post-critique improvement applied:

- Used one shared `PERSONA_PROMPT_REQUIRED_SECTIONS` constant in `tests/test_master_prompts.py` for both persona-style prompt variants.

Regression check after critique:

- Re-ran `python -m pytest tests/test_master_prompts.py tests/test_master_prompts_cli.py tests/test_master_prompt_session_injection.py`.
- Re-ran the direct prompt/source equality check.
