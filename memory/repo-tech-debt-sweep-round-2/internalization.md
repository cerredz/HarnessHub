### 1a: Structural Survey

Repository baseline for this second sweep:

- The active root checkout is a dirty user branch with substantial tracked and untracked changes.
- The implementation baseline for this sweep is `origin/main`, inspected through the clean worktree at `.worktrees/survey-round-2`.
- The repository is a Python SDK / CLI project with package source under `harnessiq/`, tests under `tests/`, docs under `docs/`, planning artifacts under `memory/`, and architecture inventory under `artifacts/`.

Top-level architecture on `origin/main`:

- `harnessiq/agents/`: long-running agent implementations and orchestration entrypoints.
- `harnessiq/cli/`: argparse-based CLI surfaces for agents and ledger workflows.
- `harnessiq/config/`: repo and runtime credential/config loading.
- `harnessiq/integrations/`: Playwright and model integrations.
- `harnessiq/master_prompts/`: prompt registry and prompt assets.
- `harnessiq/providers/`: provider HTTP clients, tracing, browser runtime helpers, and provider-adjacent utilities.
- `harnessiq/shared/`: shared dataclasses, constants, prepared-request models, and operation metadata that multiple layers re-export.
- `harnessiq/tools/`: MCP-style tool factories and tool execution surfaces.
- `harnessiq/toolset/`: higher-level catalog and registry for listing and resolving tools by key or family.
- `harnessiq/utils/`: cross-cutting runtime utilities such as ledger and storage helpers.
- `tests/`: mostly `unittest` and `pytest` coverage for package surfaces, provider/tool behavior, agent runtime behavior, CLI paths, and packaging smoke.

Technology stack and conventions:

- Python 3.11-style code with `dataclass(slots=True)` / `dataclass(frozen=True, slots=True)` used heavily for shared models.
- CLI code uses `argparse`.
- Tests mix `unittest` and `pytest`.
- Public package surfaces are intentionally stable and are checked by package-smoke tests such as `tests/test_sdk_package.py`.
- Compatibility facades are already an accepted pattern in this repo: public modules often re-export implementation that lives elsewhere.
- Error handling favors explicit `ValueError` / `KeyError` messages naming the offending key or missing requirement.
- Provider-backed helpers tend to use small client classes with injected `request_executor`.

Current maintainability observations from the second sweep:

- `harnessiq/shared/resend.py` is a 453-line mixed-responsibility module: shared constants, credentials, operation model types, path-builder helpers, catalog assembly, and catalog lookup all live together.
- `harnessiq/providers/output_sinks.py` is a 246-line mixed-responsibility module: provider-side sink transport clients and model-metadata extraction logic are co-located.
- `harnessiq/toolset/catalog.py` is a 303-line mixed-responsibility module: builtin family factories, provider metadata entries, provider key index, and provider factory dispatch are all stored in one file.

Relevant test strategy for these hotspots:

- Resend behavior is covered by `tests/test_resend_tools.py`, `tests/test_email_agent.py`, and package export checks in `tests/test_sdk_package.py`.
- Output sink behavior is covered by `tests/test_output_sinks.py`, ledger CLI coverage in `tests/test_ledger_cli.py`, agent runtime coverage in `tests/test_agents_base.py`, and provider export checks via `tests/test_providers.py`.
- Toolset catalog and registry behavior is covered by `tests/test_toolset_registry.py` and package import smoke in `tests/test_sdk_package.py`.

Repository consistency / inconsistency notes:

- The codebase is generally converging on shared-definition modules plus compatibility re-exports.
- Several public surfaces still contain monolithic metadata catalogs or mixed responsibilities even after recent cleanup.
- Open issues already cover some adjacent cleanup areas, especially package-export normalization (`#180`) and broad pytest-baseline stabilization (`#203`), so this sweep must avoid duplicating those scopes.

### 1b: Task Cross-Reference

User task for this turn: repeat the prior repo sweep process end to end, identify additional tech debt and readability / maintainability opportunities, create GitHub issues, implement each in isolated worktrees, and open PRs for each.

Concrete mapping for this second pass:

- Prior sweep already created and implemented:
  - `#205` CLI helper consolidation
  - `#207` ledger decomposition
  - `#206` Resend tool-module decomposition
- This second pass focuses on net-new, still-untracked maintainability work on `origin/main`.

New candidate surfaces mapped to the codebase:

1. Shared Resend metadata/catalog decomposition
- Primary module: `harnessiq/shared/resend.py`
- Adjacent public surfaces: `harnessiq/tools/resend.py`, `harnessiq/tools/__init__.py`, `harnessiq/shared/email.py`
- Tests: `tests/test_resend_tools.py`, `tests/test_email_agent.py`, `tests/test_sdk_package.py`
- Behavior to preserve: public shared Resend class/function names, operation catalog size and names, `ResendCredentials.__module__ == "harnessiq.shared.resend"` package contract.

2. Provider output-sink utility decomposition
- Primary module: `harnessiq/providers/output_sinks.py`
- Adjacent surfaces: `harnessiq/providers/__init__.py`, `harnessiq/agents/base/agent.py`, `harnessiq/utils/ledger.py`
- Tests: `tests/test_output_sinks.py`, `tests/test_ledger_cli.py`, `tests/test_agents_base.py`, `tests/test_providers.py`
- Behavior to preserve: transport client request preparation, `extract_model_metadata()` behavior, public provider imports.

3. Toolset catalog decomposition
- Primary module: `harnessiq/toolset/catalog.py`
- Adjacent surfaces: `harnessiq/toolset/registry.py`, `harnessiq/toolset/__init__.py`, `harnessiq/tools/leads/operations.py`
- Tests: `tests/test_toolset_registry.py`, `tests/test_arxiv_provider.py`, package smoke in `tests/test_sdk_package.py`
- Behavior to preserve: provider entry metadata, provider family dispatch strings, builtin family factory ordering, stable `ToolEntry` surface.

Blast radius:

- All three candidates are structure-preserving refactors with compatibility-facade patterns.
- Each candidate touches public import surfaces, so package-smoke and focused tests are mandatory.
- None should change user-facing CLI UX or provider/tool capability sets.

### 1c: Assumption & Risk Inventory

Assumptions:

- `origin/main` is the correct implementation baseline despite the dirty root checkout.
- Open issues `#180` and `#203` should be treated as upstream ownership of package-export normalization and broad baseline-failure cleanup respectively.
- No external consumers depend on private helper locations inside the candidate monolith modules.
- Compatibility re-exports remain the preferred mechanism for structure-preserving refactors in this repository.

Risks:

- Duplicating already-tracked work if a new ticket overlaps too much with `#180`, `#203`, or the prior sweep tickets.
- Accidentally breaking package-surface contracts checked by `tests/test_sdk_package.py`, especially `__module__` expectations for shared classes.
- Refactoring against the wrong codebase state if work accidentally targets the dirty root checkout instead of `origin/main`.
- Some verification suites still have unrelated baseline failures on `origin/main`; these must be documented rather than misattributed to new refactors.

Mitigations:

- Draft only narrowly scoped decomposition tickets with explicit drift guards.
- Preserve public import anchors and verify compatibility with focused tests plus package-smoke coverage.
- Implement every ticket in a dedicated worktree from `origin/main`.
- Record unrelated baseline failures explicitly in ticket quality artifacts.

Phase 1 complete.
