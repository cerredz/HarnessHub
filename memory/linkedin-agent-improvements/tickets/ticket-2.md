# Ticket 2: Add JobSearchConfig parameter to agent and CLI

**Title:** Add structured `job_search_config` parameter mirroring LinkedIn's filter UI

**Intent:** The user wants to pass job search criteria that maps directly to LinkedIn's filter system — title, location, remote type, experience level, date posted, easy apply preference, salary range, job type, companies, industries — either as a plain string or a structured JSON object. This should be easy to pass via SDK constructor or CLI flag and should appear in the agent's context window.

**Scope:**
- Adds `JobSearchConfig` dataclass to `harnessiq/shared/linkedin.py`
- Adds `JOB_SEARCH_CONFIG_FILENAME = "job_search_config.json"` constant
- Adds `job_search_config_path` property, `write_job_search_config()`, `read_job_search_config()` to `LinkedInMemoryStore`
- Updates `prepare()` to initialize `job_search_config.json`
- Adds `job_search_config: str | dict[str, Any] | JobSearchConfig | None = None` to `LinkedInJobApplierAgent.__init__()`
- Updates `prepare()` in the agent to persist constructor-supplied job_search_config to memory
- Updates `from_memory()` to accept `job_search_config` override
- Updates `load_parameter_sections()` to include "Job Search Config" section when non-empty
- Adds `--job-description TEXT` and `--job-description-file PATH` to the `configure` CLI command
- Does NOT remove `job_preferences.md` or its section (backward compat)

**Relevant Files:**
- `harnessiq/shared/linkedin.py` — add `JobSearchConfig`, `JOB_SEARCH_CONFIG_FILENAME`
- `harnessiq/agents/linkedin/agent.py` — add param, update prepare/load_parameter_sections/from_memory
- `harnessiq/cli/linkedin/commands.py` — add `--job-description` and `--job-description-file`
- `tests/test_linkedin_agent.py` — add tests for job_search_config

**Approach:**
`JobSearchConfig` stores all LinkedIn filter fields as optional typed attributes. `as_dict()` omits falsy values for clean JSON serialization. `render()` produces a human-readable string for context window injection. `from_string(s)` constructs a config with only `description` set.

CLI `--job-description` accepts either plain text or a JSON object string (auto-detected via `json.loads()` attempt). `--job-description-file` accepts a path to a file with the same auto-detection logic. Both write to `job_search_config.json` via `write_job_search_config()`.

Section appears in `load_parameter_sections()` only when `read_job_search_config()` returns a non-empty config, inserted after "Jobs Already Applied To" and before "Job Preferences".

**Assumptions:**
- `job_search_config` is additive alongside `job_preferences`; both may be present
- SDK usage: constructor param written to memory in `prepare()`, which runs at start of `run()`
- `from_memory()` override takes precedence over persisted file

**Acceptance Criteria:**
- [ ] `JobSearchConfig` dataclass exists in `harnessiq/shared/linkedin.py` with fields: title, location, remote_type, experience_levels, date_posted, easy_apply_only, salary_min, salary_max, job_type, companies, industries, description
- [ ] `as_dict()` omits None and empty fields; `render()` produces readable text; `is_empty()` returns True for all-default instance
- [ ] `LinkedInMemoryStore` has `write_job_search_config()` accepting str | dict | JobSearchConfig and `read_job_search_config()` returning `JobSearchConfig | None`
- [ ] Agent constructor accepts `job_search_config` param; `prepare()` writes it to memory when non-None
- [ ] `load_parameter_sections()` includes "Job Search Config" section when config is non-empty
- [ ] CLI `--job-description "text"` stores as `{"description": "text"}` in job_search_config.json
- [ ] CLI `--job-description '{"title": "Engineer", "location": "NYC"}'` stores as structured config
- [ ] All existing tests pass; new tests cover the new sections and parameters

**Verification Steps:**
1. `python -m pytest tests/test_linkedin_agent.py -v`
2. Manually test: `harnessiq linkedin configure --agent test --job-description "senior engineer"`
3. Manually test: `harnessiq linkedin configure --agent test --job-description '{"title": "SWE", "location": "NYC", "easy_apply_only": true}'`
4. Verify `job_search_config.json` written to memory path

**Dependencies:** Ticket 1 (master_prompt.md must be in place so INPUT DESCRIPTION can reference Job Search Config)

**Drift Guard:** Does not remove or rename existing `job_preferences.md`, `write_job_preferences()`, or the "Job Preferences" section. Does not modify browser tool definitions. Does not touch exa_outreach, knowt, or other agents.
