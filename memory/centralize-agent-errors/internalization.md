## 1a: Structural Survey

- Runtime source of truth is `harnessiq/`; `artifacts/file_index.md` confirms the package boundaries and current conventions.
- `harnessiq/agents/` contains the agent runtime hierarchy:
  - `base/` owns the shared run loop and helper mixins.
  - `provider_base/`, `email/`, `exa/`, `apollo/`, `instantly/`, and `outreach/` provide reusable scaffolding for provider-backed agents.
  - Concrete agents include `instagram`, `linkedin`, `knowt`, `exa_outreach`, `leads`, `prospecting`, and `research_sweep`.
- `harnessiq/shared/` owns shared runtime types, manifests, provider metadata, durable-memory models, and a small number of existing custom exceptions such as `ProviderFormatError` and `ProviderHTTPError`.
- Current error handling is inconsistent:
  - agent classes mostly raise builtin `ValueError`, `FileNotFoundError`, and `RuntimeError`;
  - provider/shared modules already introduce some custom exception types;
  - no centralized application taxonomy exists for common validation, missing-resource, or invalid-state failures.
- Test strategy is `unittest` plus `pytest`, with focused agent tests under `tests/test_*agent*.py` and scaffold tests in `tests/test_provider_base_agents.py`.

## 1b: Task Cross-Reference

- User request: define centralized shared exceptions and apply them across agent classes as a small refactor.
- Shared insertion point:
  - add `harnessiq/shared/exceptions.py` as the canonical taxonomy module.
  - update `harnessiq/shared/__init__.py` to export the shared exception types.
- Existing shared custom errors that should fit the taxonomy:
  - `harnessiq/shared/providers.py:12` defines `ProviderFormatError`.
  - `harnessiq/shared/http.py:25` defines `ProviderHTTPError`.
- Agent classes with explicit exception call sites to refactor:
  - `harnessiq/agents/provider_base/agent.py`
  - `harnessiq/agents/email/agent.py`
  - `harnessiq/agents/exa/agent.py`
  - `harnessiq/agents/apollo/agent.py`
  - `harnessiq/agents/instantly/agent.py`
  - `harnessiq/agents/outreach/agent.py`
  - `harnessiq/agents/instagram/agent.py`
  - `harnessiq/agents/knowt/agent.py`
  - `harnessiq/agents/exa_outreach/agent.py`
  - `harnessiq/agents/prospecting/agent.py`
  - `harnessiq/agents/research_sweep/agent.py`
  - `harnessiq/agents/leads/agent.py`
  - `harnessiq/agents/linkedin/agent.py`
- Concrete patterns in those files map cleanly to a small taxonomy:
  - constructor/configuration validation -> shared validation/configuration error
  - missing prompt/resources -> shared not-found error
  - invalid lifecycle/runtime state -> shared state error
- Relevant tests likely affected:
  - `tests/test_provider_base_agents.py`
  - `tests/test_exa_outreach_agent.py`
  - `tests/test_knowt_agent.py`
  - `tests/test_linkedin_agent.py`
- Compatibility requirement:
  - existing tests and callers frequently catch builtin exception families, so the new exceptions should preserve `isinstance(..., ValueError/FileNotFoundError/RuntimeError)` behavior.

## 1c: Assumption & Risk Inventory

- Assumption: the user wants a lightweight taxonomy focused on agent-layer errors, not a repo-wide rewrite of every `ValueError` in `harnessiq/shared/`.
- Assumption: backward compatibility matters more than maximal taxonomy purity, so multiple inheritance from builtin exception classes is acceptable.
- Risk: changing exception classes without preserving builtin inheritance would break current tests and caller expectations.
- Risk: broadening the refactor into helpers, tools, and all shared models would exceed the requested “simple and small” scope.
- Risk: changing message text would create avoidable test churn; message bodies should stay unchanged.

Phase 1 complete.
