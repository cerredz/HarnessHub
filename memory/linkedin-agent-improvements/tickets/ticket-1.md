# Ticket 1: LinkedIn master prompt file

**Title:** Create `master_prompt.md` for the LinkedIn agent and load it from disk

**Intent:** The current system prompt is built programmatically from a handful of hardcoded sentences and 7 behavioral rules. This is too thin for an agent driving real browser automation. The prompt needs to be a comprehensive behavioral specification covering search strategy, job qualification logic, Easy Apply multi-step flows, external application handling, form-filling rules, error recovery, and state management — with enough behavioral precision that the agent operates reliably without human correction.

**Scope:**
- Creates `harnessiq/agents/linkedin/prompts/__init__.py` (empty marker)
- Creates `harnessiq/agents/linkedin/prompts/master_prompt.md` — comprehensive prompt with `{{AGENT_IDENTITY}}`, `{{TOOL_LIST}}`, `{{ACTION_LOG_WINDOW}}` placeholders
- Updates `DEFAULT_AGENT_IDENTITY` in `harnessiq/shared/linkedin.py` to a 4-paragraph expert identity
- Updates `build_system_prompt()` in `harnessiq/agents/linkedin/agent.py` to load from file and perform template substitution
- Does NOT change parameter sections, memory files, or CLI

**Relevant Files:**
- `harnessiq/agents/linkedin/prompts/master_prompt.md` — NEW
- `harnessiq/agents/linkedin/prompts/__init__.py` — NEW (empty)
- `harnessiq/shared/linkedin.py` — update `DEFAULT_AGENT_IDENTITY`
- `harnessiq/agents/linkedin/agent.py` — update `build_system_prompt()`
- `tests/test_linkedin_agent.py` — verify key sections still present

**Approach:** Load `master_prompt.md` from `Path(__file__).parent / "prompts" / "master_prompt.md"` using a module-level `_MASTER_PROMPT_PATH` constant (same pattern as `ExaOutreachAgent`). `build_system_prompt()` reads the file and substitutes `{{AGENT_IDENTITY}}` (from memory or default), `{{TOOL_LIST}}` (from registered tools), and `{{ACTION_LOG_WINDOW}}` (from config).

**Assumptions:** All existing tests that check `"[IDENTITY]"` and `"[GOAL]"` in the system prompt will pass because the new master_prompt.md uses the same section headers.

**Acceptance Criteria:**
- [ ] `harnessiq/agents/linkedin/prompts/master_prompt.md` exists and contains `[IDENTITY]`, `[GOAL]`, `[INPUT DESCRIPTION]`, `[TOOLS]`, `[BEHAVIORAL RULES]` sections
- [ ] `build_system_prompt()` reads from the file (not hardcoded strings) and produces a complete prompt
- [ ] Template substitution replaces `{{AGENT_IDENTITY}}`, `{{TOOL_LIST}}`, `{{ACTION_LOG_WINDOW}}` correctly
- [ ] `DEFAULT_AGENT_IDENTITY` is 4 paragraphs covering: expert matching judgment, precise browser operation, user data fidelity, state persistence
- [ ] All existing tests pass

**Verification Steps:**
1. `python -m pytest tests/test_linkedin_agent.py -v` — all tests pass
2. Manually instantiate agent with temp dir and verify `build_system_prompt()` output contains new behavioral rules content

**Dependencies:** None

**Drift Guard:** No changes to memory files, parameter sections, CLI interface, or data classes. This ticket is limited to the system prompt text and how it is loaded.
