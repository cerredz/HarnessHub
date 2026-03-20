### 1a: Structural Survey

Repository shape:
- `harnessiq/` is the shipped SDK package.
- `harnessiq/agents/` contains harness orchestration layers built on `BaseAgent`.
- `harnessiq/shared/` holds reusable configs, constants, durable memory models, and cross-module contracts.
- `harnessiq/cli/` maps persisted memory plus factories/config into runnable agent commands.
- `harnessiq/utils/` contains generic runtime persistence helpers such as ledger and run storage.
- `tests/` covers agent harnesses, CLI entrypoints, shared models, provider tracing, and package smoke rules.

Technology and conventions:
- Python package with `pytest` coverage as the primary quality gate.
- Agent harnesses should keep reusable configs/constants in `harnessiq/shared/` and keep behavior-heavy orchestration in `harnessiq/agents/`.
- CLI commands are thin adapters that load memory/config, construct an agent, run it, and emit summaries.
- `artifacts/file_index.md` and `tests/test_sdk_package.py` enforce that shared definitions do not live in agent/provider implementation modules.

Current repo state from a clean worktree on refreshed `origin/main`:
- Full suite result before fixes: `34 failed, 1207 passed, 1 warning`.
- Previously verified breakages on `main` already had clean fixes on prior branches:
  - ExaOutreach storage contract drift and CLI JSON serialization.
  - `ProviderHTTPError` being frozen and breaking traceback propagation through traced re-raises.
- Remaining red clusters localize to:
  - `harnessiq/agents/base/agent.py`
  - `harnessiq/agents/leads/agent.py`
  - `harnessiq/utils/ledger.py`
  - `harnessiq/shared/tools.py`
  - `harnessiq/tools/reasoning/injectable.py`
  - `harnessiq/agents/knowt/agent.py`
  - `harnessiq/agents/exa_outreach/agent.py`
  - `harnessiq/agents/prospecting/agent.py`

### 1b: Task Cross-Reference

User request:
- "fix everything that is broken and then create a pr into main"

Interpretation mapped to the codebase:
- "everything broken" is scoped to reproducible failures on refreshed `main` from the clean worktree, verified by `pytest -q`.
- The request therefore maps to the full current red set, not only the earlier Exa-specific failures.

Concrete failure mapping:
- ExaOutreach:
  - `harnessiq/shared/exa_outreach.py`
  - `harnessiq/cli/exa_outreach/commands.py`
  - `harnessiq/shared/http.py`
  - `tests/test_exa_outreach_agent.py`
  - `tests/test_exa_outreach_cli.py`
  - `tests/test_exa_outreach_shared.py`
  - `tests/test_providers.py`
- Base agent prune/reset regression:
  - `harnessiq/agents/base/agent.py`
  - `tests/test_agents_base.py`
- Leads harness constructor regression:
  - `harnessiq/agents/leads/agent.py`
  - `tests/test_leads_agent.py`
  - `tests/test_leads_cli.py`
- Ledger home-directory fallback regression:
  - `harnessiq/utils/ledger.py`
  - `tests/test_linkedin_cli.py`
- Reasoning tool count/preset regressions:
  - `harnessiq/shared/tools.py`
  - `harnessiq/tools/reasoning/injectable.py`
  - `tests/test_reasoning_tools.py`
- Knowt runtime-config preservation regression:
  - `harnessiq/agents/knowt/agent.py`
  - `tests/test_knowt_agent.py`
- Shared-definition placement violations:
  - `harnessiq/agents/exa_outreach/agent.py`
  - `harnessiq/agents/prospecting/agent.py`
  - likely corresponding shared homes:
    - `harnessiq/shared/exa_outreach.py`
    - `harnessiq/shared/prospecting.py`
  - `tests/test_sdk_package.py`

Behavior that must be preserved:
- Existing agent public APIs and CLI surfaces.
- Existing durable memory formats and ledger outputs.
- Existing provider-tracing semantics aside from restoring correct exception propagation.
- Existing package imports that expect shared definitions to remain re-exported from stable surfaces.

### 1c: Assumption & Risk Inventory

Assumptions:
- The correct completion bar is a clean `pytest -q` run on refreshed `main`.
- External `403` responses from Exa/xAI are environmental and not part of the code-fix scope unless tests assert around them.
- One stabilization PR is preferable to multiple narrowly-scoped PRs because the user explicitly asked for a single fix-everything pass.

Risks:
- Some failures are independent regressions introduced on `main`, while others are already solved on prior topic branches; mixing those cleanly without regressing stable code requires disciplined backports.
- Shared-definition cleanup can introduce circular imports if constants/configs are moved into the wrong shared module.
- The repo root checkout is dirty, so all implementation must remain isolated to this clean worktree.

No clarifying questions are required. The failing test set makes the target behavior concrete.

Phase 1 complete
