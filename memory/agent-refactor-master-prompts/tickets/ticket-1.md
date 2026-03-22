# Ticket 1: Refactor agents into individual subfolders with memory directories

## Intent
Reorganize `harnessiq/agents/` so that each agent has its own well-bounded subdirectory containing its implementation module(s) and a `memory/` folder. The `memory/` folder for `linkedin` becomes the default persistent memory location for `LinkedInJobApplierAgent`. This gives each agent a coherent home and makes the memory convention explicit and structural rather than implicit and caller-supplied.

## Scope
**Changes:**
- Create `harnessiq/agents/base/`, `harnessiq/agents/email/`, `harnessiq/agents/linkedin/` subpackages
- Move agent code from flat files into each subpackage's `agent.py`
- Create `memory/` subdirectory inside each agent subpackage (with `.gitkeep` for base/email)
- Make `memory_path` optional in `LinkedInJobApplierAgent.__init__` and `from_memory`, defaulting to `Path(__file__).parent / "memory"`
- Update `harnessiq/agents/__init__.py` to import from the new subpackage paths
- Delete the now-superseded flat files: `base.py`, `email.py`, `linkedin.py`

**Does not touch:**
- `harnessiq/shared/` — unchanged
- `harnessiq/cli/` — unchanged (all imports remain valid)
- All test files — unchanged (all imports remain valid)
- `harnessiq/tools/`, `harnessiq/providers/`, `harnessiq/config/` — unchanged

## Relevant Files
- CREATE `harnessiq/agents/base/__init__.py` — re-export all public symbols from `agent.py`
- CREATE `harnessiq/agents/base/agent.py` — content of former `base.py`, unchanged
- CREATE `harnessiq/agents/base/memory/.gitkeep` — structural placeholder
- CREATE `harnessiq/agents/email/__init__.py` — re-export all public symbols from `agent.py`
- CREATE `harnessiq/agents/email/agent.py` — content of former `email.py`; update relative import `from harnessiq.agents.base import ...` → unchanged (still valid)
- CREATE `harnessiq/agents/email/memory/.gitkeep` — structural placeholder
- CREATE `harnessiq/agents/linkedin/__init__.py` — re-export all public symbols from `agent.py`
- CREATE `harnessiq/agents/linkedin/agent.py` — content of former `linkedin.py`; `memory_path` made optional; import of `base.BaseAgent` updated to `harnessiq.agents.base`
- CREATE `harnessiq/agents/linkedin/memory/.gitkeep` — default runtime memory location placeholder
- MODIFY `harnessiq/agents/__init__.py` — imports updated to new relative subpackage paths
- DELETE `harnessiq/agents/base.py`
- DELETE `harnessiq/agents/email.py`
- DELETE `harnessiq/agents/linkedin.py`

## Approach
Convert each flat module to a package of the same name. Python resolves `harnessiq.agents.base` identically whether `base` is a `.py` file or a directory with `__init__.py` — so all existing imports in tests and CLI are backward-compatible with zero changes. Each agent's logic is placed in `agent.py` within its subpackage, and the `__init__.py` re-exports the full public surface. The `_DEFAULT_MEMORY_PATH` constant in `linkedin/agent.py` is derived via `Path(__file__).parent / "memory"` so it works correctly regardless of where the package is installed.

## Assumptions
- All existing import paths in `tests/` and `harnessiq/cli/` remain valid after the refactor because Python resolves the subpackage `__init__.py` identically to the old flat module.
- The `memory/` folder for `base` and `email` agents is a structural placeholder; runtime state will be added to these in future tickets.
- The `.gitkeep` file convention is used for empty directories.

## Acceptance Criteria
- [ ] `harnessiq/agents/base.py`, `email.py`, and `linkedin.py` no longer exist as flat files
- [ ] `harnessiq/agents/base/`, `email/`, `linkedin/` directories each contain `__init__.py`, `agent.py`, and `memory/`
- [ ] `from harnessiq.agents import BaseAgent, BaseEmailAgent, LinkedInJobApplierAgent` works
- [ ] `from harnessiq.agents.base import BaseAgent` works
- [ ] `from harnessiq.agents.email import BaseEmailAgent, EmailAgentConfig` works
- [ ] `from harnessiq.agents.linkedin import LinkedInJobApplierAgent, LinkedInMemoryStore, SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS, normalize_linkedin_runtime_parameters` works
- [ ] `LinkedInJobApplierAgent(model=model)` (no `memory_path`) defaults to `harnessiq/agents/linkedin/memory/`
- [ ] `LinkedInJobApplierAgent(model=model, memory_path="/tmp/x")` still respects the explicit path
- [ ] All existing tests pass without modification

## Verification Steps
1. `python -m pytest tests/ -x -q` — full suite passes
2. `python -c "from harnessiq.agents import BaseAgent, BaseEmailAgent, LinkedInJobApplierAgent, LinkedInMemoryStore; print('OK')"` — no import errors
3. `python -c "from harnessiq.agents.linkedin import SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS, normalize_linkedin_runtime_parameters; print('OK')"` — CLI deep import still valid
4. Manual check: `harnessiq/agents/linkedin/memory/` directory exists in the repository

## Dependencies
None.

## Drift Guard
This ticket is a pure structural refactor. It must not change any behavior of the agent loop, the tool registry, the system prompt generation, the memory store read/write logic, or the CLI. The only behavioral delta allowed is making `memory_path` optional in `LinkedInJobApplierAgent` with a sensible default. Any temptation to refactor the internals of the agent implementations is out of scope.
