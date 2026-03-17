### 1a: Structural Survey

**Repository shape:**
- `harnessiq/agents/linkedin/agent.py` — `LinkedInMemoryStore` (durable state) + `LinkedInJobApplierAgent` (harness). 952 lines.
- `harnessiq/shared/linkedin.py` — Constants, data classes (`LinkedInAgentConfig`, `JobApplicationRecord`, `ActionLogEntry`, `LinkedInManagedFile`). 165 lines.
- `harnessiq/cli/linkedin/commands.py` — 5 CLI commands: prepare, configure, show, run, init-browser. 387 lines.
- `harnessiq/agents/linkedin/memory/` — Default memory root (only `.gitkeep`).
- `harnessiq/agents/exa_outreach/agent.py` — Reference pattern for master_prompt.md loading.
- `harnessiq/agents/linkedin/prompts/` — Does NOT exist yet.

**Context window structure:**
- Zone 1: System prompt (`build_system_prompt()`) — currently built programmatically with `[IDENTITY]`, `[GOAL]`, `[INPUT DESCRIPTION]`, `[TOOLS]`, `[BEHAVIORAL RULES]`. Very thin (7 rules).
- Zone 2: Parameter sections (`load_parameter_sections()`) — currently: Job Preferences, User Profile, Jobs Already Applied To, Recent Actions, optional: Runtime/Custom/Additional Prompt/Managed Files.
- Zone 3: Rolling transcript.

**Agent constructor parameters (current):** model, memory_path, browser_tools, screenshot_persistor, max_tokens, reset_threshold, action_log_window, linkedin_start_url, notify_on_pause, pause_webhook.

**Memory files (current):**
- `job_preferences.md`, `user_profile.md`, `agent_identity.md`
- `applied_jobs.jsonl`, `action_log.jsonl`
- `runtime_parameters.json`, `custom_parameters.json`, `additional_prompt.md`
- `managed_files.json`, `screenshots/`, `managed_files/`

**ExaOutreach master prompt pattern:**
- File: `harnessiq/agents/exa_outreach/prompts/master_prompt.md`
- Loaded via `_MASTER_PROMPT_PATH = Path(__file__).parent / "prompts" / "master_prompt.md"`
- Static file with no placeholders (identity and behavioral content are fixed inline).

**LinkedIn system prompt pattern (current):**
- `build_system_prompt()` dynamically builds from: identity (memory), tool list (dynamic), hardcoded goal/rules.
- Must keep dynamic injection of tool list and action_log_window.

### 1b: Task Cross-Reference

| Request | Current State | Gap |
|---------|--------------|-----|
| Better master prompt | Thin programmatic prompt (7 rules, 3-sentence goal) | Need `prompts/master_prompt.md` with comprehensive behavioral spec; update `build_system_prompt()` to load it |
| Job description param (string or JSON) | Only `job_preferences.md` (free text) | Need `JobSearchConfig` dataclass + `job_search_config.json` + agent constructor param + CLI flag |
| Custom instructions param | Exists as `additional_prompt.md` with `--additional-prompt-text/file` CLI flags | Need to rename CLI flags to `--custom-instructions-*`; rename section title to "Custom Instructions" |
| Applied jobs first in context window | Currently 3rd section (after Job Preferences, User Profile) | Move to 1st position in `load_parameter_sections()` |
| Applied jobs saved to memory | Already works via `applied_jobs.jsonl` | Just verify order; no logic change needed |

**Files touched:**
- `harnessiq/shared/linkedin.py` — Add `JobSearchConfig`, `JOB_SEARCH_CONFIG_FILENAME`
- `harnessiq/agents/linkedin/agent.py` — Load master prompt, add params, reorder sections
- `harnessiq/agents/linkedin/prompts/master_prompt.md` — NEW FILE
- `harnessiq/cli/linkedin/commands.py` — Rename `--additional-prompt` → `--custom-instructions`, add `--job-description`
- `tests/test_linkedin_agent.py` — Update for new section order + new sections

### 1c: Assumption & Risk Inventory

1. **JobSearchConfig vs job_preferences**: Adding new `job_search_config.json` alongside existing `job_preferences.md`. Both will appear in context window if both are set. Kept `job_preferences` for backward compat, `job_search_config` is additive.

2. **additional_prompt rename**: Renaming CLI flag only (`--additional-prompt` → `--custom-instructions`), keeping underlying file (`additional_prompt.md`) and Python method names unchanged to avoid breaking persisted state. Section title changed from "Additional Prompt Data" → "Custom Instructions".

3. **master_prompt.md placeholders**: Will use `{{AGENT_IDENTITY}}`, `{{TOOL_LIST}}`, `{{ACTION_LOG_WINDOW}}` as template substitution targets in `build_system_prompt()`.

4. **DEFAULT_AGENT_IDENTITY**: Needs to be upgraded from 3 lines to 4 comprehensive paragraphs that match the master prompt quality bar.

5. **Test breakage**: `test_run_bootstraps_memory_files_and_injects_linkedin_prompt_sections` checks exact section title order — will need updating for: (a) applied jobs moved to first, (b) new job_search_config section, (c) "Additional Prompt Data" → "Custom Instructions".

Phase 1 complete.
