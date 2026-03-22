# Ticket 2: ExaOutreach Shared Types, Memory Store, and Storage Backend

## Title
Add shared data models, memory store, and storage backend for ExaOutreachAgent

## Intent
Establish the durable state layer for the ExaOutreach agent: the `EmailTemplate` data model, `OutreachRunLog` record types, the `StorageBackend` protocol for pluggable persistence, `FileSystemStorageBackend` (default), and `ExaOutreachMemoryStore` which manages per-run JSON files under the agent's memory path. Also adds the 5 new tool key constants to `harnessiq/shared/tools.py`.

## Scope
**Creates:**
- `harnessiq/shared/exa_outreach.py` — all shared types and memory store
- `tests/test_exa_outreach_shared.py` — unit tests

**Modifies:**
- `harnessiq/shared/tools.py` — add 5 new tool key constants + re-export them in `__all__`

**Does NOT touch:**
- Agent harness (Ticket 3)
- CLI (Ticket 4)
- `harnessiq/agents/__init__.py`

## Relevant Files
- `harnessiq/shared/exa_outreach.py` — NEW; contains all types, store, backends
- `harnessiq/shared/tools.py` — ADD constants: `EXA_OUTREACH_LIST_TEMPLATES`, `EXA_OUTREACH_GET_TEMPLATE`, `EXA_OUTREACH_CHECK_CONTACTED`, `EXA_OUTREACH_LOG_LEAD`, `EXA_OUTREACH_LOG_EMAIL_SENT`
- `tests/test_exa_outreach_shared.py` — NEW

Reference for patterns:
- `harnessiq/shared/linkedin.py` — follow the same dataclass + file-io conventions
- `harnessiq/shared/knowt.py` — simpler memory store for contrast

## Approach

### EmailTemplate
```python
@dataclass(frozen=True, slots=True)
class EmailTemplate:
    id: str
    title: str
    subject: str
    description: str
    actual_email: str
    links: tuple[str, ...] = ()
    pain_points: tuple[str, ...] = ()
    icp: str = ""
    extra: dict[str, Any] = field(default_factory=dict)  # open-ended metadata
```
`from_dict(d)` / `as_dict()` methods for JSON round-tripping.

### LeadRecord and EmailSentRecord
```python
@dataclass
class LeadRecord:
    url: str
    name: str
    email_address: str | None
    found_at: str  # UTC ISO
    notes: str | None

@dataclass
class EmailSentRecord:
    to_email: str
    to_name: str
    subject: str
    template_id: str
    sent_at: str  # UTC ISO
    notes: str | None
```

### OutreachRunLog
```python
@dataclass
class OutreachRunLog:
    run_id: str          # "run_1", "run_2", ...
    started_at: str
    completed_at: str | None
    query: str
    leads_found: list[LeadRecord]
    emails_sent: list[EmailSentRecord]
```
Serializes to/from JSON. `run_id` format: `run_{N}`.

### StorageBackend (Protocol)
```python
class StorageBackend(Protocol):
    def start_run(self, run_id: str, query: str) -> None: ...
    def finish_run(self, run_id: str, completed_at: str) -> None: ...
    def log_lead(self, run_id: str, lead: LeadRecord) -> None: ...
    def log_email_sent(self, run_id: str, record: EmailSentRecord) -> None: ...
    def is_contacted(self, url: str) -> bool: ...
    def current_run_id(self) -> str | None: ...
```

### FileSystemStorageBackend
- Writes `run_{N}.json` under `memory_path/runs/`
- `is_contacted(url)` scans all existing run files for the URL
- Thread-safety: not required (single-agent, single-process)
- `start_run` creates the file; `finish_run` updates `completed_at`; `log_lead`/`log_email_sent` read-modify-write the file

### ExaOutreachMemoryStore
```python
@dataclass(slots=True)
class ExaOutreachMemoryStore:
    memory_path: Path

    def prepare(self) -> None: ...  # mkdir, default files
    def next_run_id(self) -> str: ...  # count existing run files
    def read_query_config(self) -> dict[str, Any]: ...
    def write_query_config(self, config: dict[str, Any]) -> None: ...
    def read_agent_identity(self) -> str: ...
    def write_agent_identity(self, text: str) -> None: ...
    def read_additional_prompt(self) -> str: ...
    def write_additional_prompt(self, text: str) -> None: ...
    def list_run_files(self) -> list[Path]: ...  # sorted by run number
    def read_run(self, run_id: str) -> OutreachRunLog: ...
```

### Tool key constants added to harnessiq/shared/tools.py
```
EXA_OUTREACH_LIST_TEMPLATES = "exa_outreach.list_templates"
EXA_OUTREACH_GET_TEMPLATE = "exa_outreach.get_template"
EXA_OUTREACH_CHECK_CONTACTED = "exa_outreach.check_contacted"
EXA_OUTREACH_LOG_LEAD = "exa_outreach.log_lead"
EXA_OUTREACH_LOG_EMAIL_SENT = "exa_outreach.log_email_sent"
```

## Assumptions
- `email_data` is provided as a list; the agent constructor converts each dict to `EmailTemplate` via `EmailTemplate.from_dict(d)`.
- `is_contacted` uses the Exa profile URL as the unique identifier (not email address, since email discovery via Exa is not guaranteed).
- File writes are synchronous (no async needed).
- Run file naming: `run_1.json`, `run_2.json`, etc. (no zero-padding, consistent with user spec).

## Acceptance Criteria
- [ ] `EmailTemplate.from_dict` round-trips through `as_dict()` with no data loss
- [ ] `EmailTemplate` with minimal fields (only required fields) instantiates without error
- [ ] `FileSystemStorageBackend.start_run` creates `run_{N}.json` under `memory_path/runs/`
- [ ] `FileSystemStorageBackend.log_lead` appends a lead to the run file without corrupting existing data
- [ ] `FileSystemStorageBackend.log_email_sent` appends an email sent record to the run file
- [ ] `FileSystemStorageBackend.is_contacted(url)` returns True when URL appears in any existing run
- [ ] `FileSystemStorageBackend.finish_run` sets `completed_at` on the run file
- [ ] `ExaOutreachMemoryStore.next_run_id` returns `"run_1"` for empty memory, `"run_N+1"` for N existing runs
- [ ] `ExaOutreachMemoryStore.prepare` creates memory dir and runs/ subdir
- [ ] `harnessiq/shared/tools.py` exports all 5 new constants in `__all__`
- [ ] All tests pass: `pytest tests/test_exa_outreach_shared.py`

## Verification Steps
1. `pytest tests/test_exa_outreach_shared.py -v` — all pass
2. `python -c "from harnessiq.shared.exa_outreach import EmailTemplate, FileSystemStorageBackend, ExaOutreachMemoryStore; print('ok')"` — no import errors
3. `python -c "from harnessiq.shared.tools import EXA_OUTREACH_LIST_TEMPLATES; print(EXA_OUTREACH_LIST_TEMPLATES)"` — prints `exa_outreach.list_templates`

## Dependencies
None — foundational ticket.

## Drift Guard
Must not touch agent harness, CLI, or any file outside `harnessiq/shared/exa_outreach.py`, `harnessiq/shared/tools.py`, and `tests/test_exa_outreach_shared.py`.
