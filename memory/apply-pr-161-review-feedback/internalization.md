### 1a: Structural Survey

- `harnessiq/agents/` contains harness classes that inherit from `BaseAgent` and should primarily own orchestration.
- `harnessiq/shared/` contains reusable domain configs, constants, dataclasses, protocols, and durable memory/store logic.
- `harnessiq/tools/` contains executable `RegisteredTool` factories and tool handlers.
- `harnessiq/toolset/` contains the static catalog and registry layer for reusable tool lookup.
- In PR #161, `harnessiq/agents/leads/agent.py` currently mixes harness orchestration with shared definitions and tool-factory responsibilities.
- Neighboring patterns confirm the intended split:
  - `harnessiq/shared/knowt.py` and `harnessiq/shared/exa_outreach.py` own domain config/state.
  - `harnessiq/tools/knowt/operations.py` owns concrete tool definitions/handlers.
  - Agents consume those layers rather than defining large tool registries inline.

### 1b: Task Cross-Reference

- PR #161 review comments require three structural fixes:
  - move configs/constants/types into `shared/`
  - put defaults into shared config
  - move the leads tool registry/tool definitions into `tools/`
- Concrete files affected:
  - `harnessiq/agents/leads/agent.py`
  - `harnessiq/shared/leads.py`
  - `harnessiq/shared/tools.py`
  - `harnessiq/tools/leads/__init__.py`
  - `harnessiq/tools/leads/operations.py`
  - `tests/test_leads_shared.py`
  - `tests/test_leads_tools.py`
  - `artifacts/file_index.md`
- Behavior to preserve:
  - `LeadsAgent` constructor and run flow
  - durable run/search/lead persistence
  - default provider-tool composition by platform family
  - public `LEADS_*` imports from the agent module

### 1c: Assumption & Risk Inventory

- Assumption: the PR comments apply to `origin/issue-153`, so implementation is happening in a dedicated worktree on that branch.
- Assumption: “toolset folder” in the comment refers to the executable tool layer under `harnessiq/tools/`, not the static catalog package under `harnessiq/toolset/`.
- Risk: moving constants/config/tool factories can break imports or alter tool ordering unless backwards compatibility is preserved.
- Risk: `artifacts/file_index.md` needs explicit boundary rules at the top; a vague folder list is not enough to prevent recurrence.

Phase 1 complete
