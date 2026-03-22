Title: Split the provider output-sink utility module into focused metadata and client layers

Intent:
Make the provider-side output sink support code easier to navigate by separating model-metadata extraction from provider-specific delivery clients, while preserving the current provider import surface used by agents and ledger sinks.

Issue URL: https://github.com/cerredz/HarnessHub/issues/213

Scope:

- Decompose `harnessiq/providers/output_sinks.py` into smaller focused modules.
- Keep `harnessiq.providers.output_sinks` as the stable import surface for existing public names.
- Preserve transport request preparation, metadata extraction heuristics, and provider package exports.
- Do not alter ledger sink payload contracts or introduce new sink providers.

Relevant Files:

- `harnessiq/providers/output_sinks.py`: convert into a compatibility facade that re-exports decomposed implementation.
- `harnessiq/providers/output_sink_clients.py`: new module for `WebhookDeliveryClient`, `NotionClient`, `ConfluenceClient`, `SupabaseClient`, and `LinearClient`.
- `harnessiq/providers/output_sink_metadata.py`: new module for `extract_model_metadata()` and its internal coercion / provider-detection helpers.
- `harnessiq/providers/__init__.py`: preserve public exports against the new internal layout.
- `tests/test_output_sinks.py`: confirm sink-facing behavior remains unchanged.
- `tests/test_agents_base.py`: confirm agent runtime metadata extraction still resolves correctly.
- `tests/test_providers.py`: confirm provider package exports still resolve as expected if relevant.

Approach:

- Split the module by responsibility: delivery clients in one module, model-metadata inference in another, compatibility facade at the public module path.
- Re-export the same public names from `harnessiq.providers.output_sinks` and `harnessiq.providers`.
- Move code with minimal semantic change so the ledger sink layer and agent runtime keep their current behavior.

Assumptions:

- Callers depend on public class/function names, not private helper locations inside `output_sinks.py`.
- The current metadata extraction heuristics are intentional behavior and should be preserved exactly unless a compatibility fix is required.
- Existing sink and agent-runtime tests cover the important external behavior of this module.

Acceptance Criteria:

- [ ] The output-sink provider implementation is split into focused metadata and client modules with `harnessiq.providers.output_sinks` remaining a compatibility facade.
- [ ] Existing public imports from `harnessiq.providers` and `harnessiq.providers.output_sinks` continue to work.
- [ ] Agent runtime metadata extraction behavior remains unchanged.
- [ ] Output sink tests continue to pass after the refactor.
- [ ] The resulting `harnessiq/providers/output_sinks.py` file is materially smaller and easier to scan.

Verification Steps:

- Static analysis: run `python -m compileall harnessiq tests`.
- Type checking: no configured type checker; keep extracted modules annotated and preserve import signatures.
- Unit tests: run `.venv\Scripts\pytest.exe -q tests/test_output_sinks.py`.
- Integration and contract tests: run `.venv\Scripts\pytest.exe -q tests/test_agents_base.py tests/test_providers.py` and document unrelated baseline failures if present.
- Smoke/manual verification: run a short `.venv\Scripts\python.exe` snippet that imports `extract_model_metadata`, `WebhookDeliveryClient`, and `LinearClient` from `harnessiq.providers`.

Dependencies:

- None.

Drift Guard:

This ticket is a provider-utility decomposition only. It must not redesign ledger sinks, change output payloads, add new provider clients, or widen into broader provider package normalization beyond what is necessary to keep the existing public imports stable.
