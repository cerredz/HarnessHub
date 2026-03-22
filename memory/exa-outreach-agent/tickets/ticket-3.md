# Ticket 3: ExaOutreachAgent Harness and Tools

## Title
Add ExaOutreachAgent harness with Exa search tools, Resend email tools, and internal outreach memory tools

## Intent
Implement the concrete `ExaOutreachAgent` class: a loop agent that searches Exa for prospects, picks email templates from the injected `email_data`, checks dedup against prior runs, sends emails via Resend, and deterministically logs all leads and sent emails to the configured storage backend inside the tool handlers themselves.

## Scope
**Creates:**
- `harnessiq/agents/exa_outreach/__init__.py`
- `harnessiq/agents/exa_outreach/agent.py` — `ExaOutreachAgent`
- `harnessiq/agents/exa_outreach/prompts/master_prompt.md` — system prompt loaded at runtime
- `tests/test_exa_outreach_agent.py`

**Modifies:**
- `harnessiq/agents/__init__.py` — export `ExaOutreachAgent`, `ExaOutreachMemoryStore`

**Does NOT touch:**
- CLI (Ticket 4)
- `harnessiq/shared/tools.py` (already done in Ticket 2)

## Relevant Files
Reference implementations (must match their conventions):
- `harnessiq/agents/knowt/agent.py` — master_prompt.md loaded from disk, ToolRegistry composition
- `harnessiq/agents/email/agent.py` — Resend tool injection pattern
- `harnessiq/agents/linkedin/agent.py` — internal `_tool_definition()` helper, `_merge_tools()`
- `harnessiq/tools/exa/operations.py` — `create_exa_tools()` factory
- `harnessiq/tools/resend.py` — `create_resend_tools()` factory

## Approach

### ExaOutreachAgentConfig
```python
@dataclass(frozen=True, slots=True)
class ExaOutreachAgentConfig:
    exa_credentials: ExaCredentials
    resend_credentials: ResendCredentials
    email_data: tuple[EmailTemplate, ...]
    search_query: str
    memory_path: Path
    storage_backend: StorageBackend  # defaults to FileSystemStorageBackend
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD
    allowed_resend_operations: tuple[str, ...] | None = None
    allowed_exa_operations: tuple[str, ...] | None = None
```
`email_data` validated: must be non-empty. `search_query` validated: must be non-blank.

### Tool registration in ExaOutreachAgent
```python
tool_registry = ToolRegistry(_merge_tools(
    create_exa_tools(credentials=config.exa_credentials,
                     allowed_operations=config.allowed_exa_operations or ("search", "get_contents", "search_and_contents")),
    create_resend_tools(credentials=config.resend_credentials,
                        allowed_operations=config.allowed_resend_operations),
    self._build_internal_tools(),
))
```

### Internal tools (5 tools)
All built via the same `_tool_definition()` helper pattern from linkedin/agent.py.

**`exa_outreach.list_templates`** — No args. Returns list of `{id, title, description, icp, pain_points}` for all templates. Agent uses this to see what's available.

**`exa_outreach.get_template`** — Args: `template_id: str`. Returns full `EmailTemplate.as_dict()`. Agent calls this to get `actual_email` + `subject` before sending.

**`exa_outreach.check_contacted`** — Args: `url: str`. Returns `{already_contacted: bool}`. Agent MUST call before sending to any URL.

**`exa_outreach.log_lead`** — Args: `url: str`, `name: str`, `email_address: str` (optional), `notes: str` (optional). Handler calls `storage_backend.log_lead(run_id, LeadRecord(...))` deterministically. Returns the logged record.

**`exa_outreach.log_email_sent`** — Args: `to_email: str`, `to_name: str`, `subject: str`, `template_id: str`, `notes: str` (optional). Handler calls `storage_backend.log_email_sent(run_id, EmailSentRecord(...))` deterministically. Returns the logged record.

### Context window structure (enforced in load_parameter_sections)
Parameter sections injected in this order:
1. `"Email Templates"` — JSON of all templates (full `as_dict()` for each)
2. `"Search Query"` — the configured `search_query` + runtime params
3. `"Current Run"` — current `run_id` so agent can reference it

### build_system_prompt
Loads `harnessiq/agents/exa_outreach/prompts/master_prompt.md` at runtime (same pattern as KnowtAgent). Raises `FileNotFoundError` with a clear message if the file is missing.

### master_prompt.md sections
```markdown
[IDENTITY]
You are ExaOutreachAgent, ...

[GOAL]
Your goal is to continuously find prospects via Exa neural search,
select appropriate email templates, and send personalized outreach...

[WORKFLOW]
1. Call exa.request with operation=search_and_contents to find prospects
2. For each prospect: call exa_outreach.check_contacted to skip duplicates
3. Call exa_outreach.log_lead to record each new lead found
4. Call exa_outreach.list_templates or exa_outreach.get_template to select email
5. Personalize the actual_email content with prospect-specific details
6. Call resend.request with operation=send_email to deliver the message
7. Call exa_outreach.log_email_sent immediately after each send
8. Repeat until you have exhausted the current search results

[BEHAVIORAL RULES]
- Never send to a URL that check_contacted returns already_contacted: true
- Always call log_email_sent immediately after a successful send
- Always call log_lead for every new prospect found, whether contacted or not
- Personalize every email — never send the actual_email template verbatim
- Do not expose API credentials in assistant messages
```

### prepare() method
```python
def prepare(self) -> None:
    self._memory_store.prepare()
    run_id = self._memory_store.next_run_id()
    self._current_run_id = run_id
    self._config.storage_backend.start_run(run_id, self._config.search_query)
```

### from_config classmethod
Convenience constructor that accepts raw dicts for `email_data` and converts them to `EmailTemplate` objects.

## Assumptions
- Depends on Ticket 2 being merged (needs `EmailTemplate`, `StorageBackend`, `ExaOutreachMemoryStore`, `FileSystemStorageBackend`).
- The master prompt is loaded at runtime, not embedded in Python, so it can be updated without touching code.
- `run_id` is determined at `prepare()` time and is stable for the entire run.
- Tool key constants (`EXA_OUTREACH_*`) from Ticket 2 are used for all internal tool keys.

## Acceptance Criteria
- [ ] `ExaOutreachAgent` instantiates successfully with valid config
- [ ] `agent.available_tools()` contains `exa.request`, `resend.request`, and all 5 internal tools
- [ ] `agent.build_system_prompt()` returns the master prompt text without error when the file exists
- [ ] `agent.build_system_prompt()` raises `FileNotFoundError` with clear message when file is missing
- [ ] `agent.load_parameter_sections()` returns sections in order: Email Templates, Search Query, Current Run
- [ ] `exa_outreach.list_templates` returns all templates with id/title/description
- [ ] `exa_outreach.get_template` returns full template dict for known ID; raises on unknown ID
- [ ] `exa_outreach.check_contacted` delegates to `storage_backend.is_contacted(url)` and returns correct bool
- [ ] `exa_outreach.log_lead` handler calls `storage_backend.log_lead` deterministically (regardless of agent behavior)
- [ ] `exa_outreach.log_email_sent` handler calls `storage_backend.log_email_sent` deterministically
- [ ] `harnessiq/agents/__init__.py` exports `ExaOutreachAgent` and `ExaOutreachMemoryStore`
- [ ] All tests pass: `pytest tests/test_exa_outreach_agent.py -v`

## Verification Steps
1. `pytest tests/test_exa_outreach_agent.py -v` — all pass
2. `python -c "from harnessiq.agents import ExaOutreachAgent; print('ok')"`
3. Manually verify parameter sections order matches spec by reading `load_parameter_sections` return value in test

## Dependencies
- Ticket 2 (shared types and memory store) must be merged first.

## Drift Guard
Must not touch CLI. Must not modify the Resend or Exa provider implementations. Internal tool keys must use the constants defined in Ticket 2.
