Title: Add Google Maps prospecting shared models and agent harness

Issue URL: https://github.com/cerredz/HarnessHub/issues/193

Intent:
Implement the new Google Maps prospecting harness in the repo’s established style: typed shared models and defaults, durable memory store, prompt asset, Playwright-backed browser integration, and a concrete agent class that evaluates listings, persists qualified leads, and emits sink-friendly ledger outputs.

Scope:
- Add shared prospecting constants, config models, record schemas, runtime/custom parameter normalization, and a durable memory store.
- Add the master prompt asset and the concrete `GoogleMapsProspectingAgent`.
- Add a Playwright-backed Google Maps/browser integration that satisfies the shared browser tool definitions introduced in Ticket 1.
- Wire the agent to use shared public tools for browser interaction, evaluation, and search-or-summarize behavior.
- Persist qualified leads and search progress in durable memory.
- Emit qualified leads by default in ledger outputs for sink export at run completion.
- Do not add CLI commands or public SDK exports in this ticket.

Relevant Files:
- `harnessiq/shared/prospecting.py`: new shared config, records, defaults, and memory store.
- `harnessiq/agents/prospecting/agent.py`: new concrete harness.
- `harnessiq/agents/prospecting/__init__.py`: agent-local exports.
- `harnessiq/agents/prospecting/prompts/master_prompt.md`: prompt asset.
- `harnessiq/integrations/google_maps_playwright.py`: Playwright-backed browser tool handlers/factory.
- `harnessiq/agents/__init__.py`: export updates if needed for agent-local import path testing.
- `tests/test_prospecting_agent.py`: direct harness coverage.
- `tests/test_google_maps_playwright.py`: integration-factory/tool-handler unit coverage.

Approach:
Mirror the LinkedIn/Instagram/ExaOutreach patterns instead of inventing a new runtime. Use a dedicated `ProspectingMemoryStore` to own durable files and typed records. Let the agent build parameter sections from that store on every window. Use Playwright-backed shared browser tool handlers to navigate Google Maps and extract structured listing/detail data. Use shared prospecting tool factories with injected model-backed runners to evaluate one company and to derive/summarize search progression. Make `qualified_leads` a ledger output so configured sinks receive them by default without changing sink semantics.

Assumptions:
- Ticket 1’s shared tool factories and browser definitions exist.
- The main model adapter can be reused for deterministic sub-calls through a small internal JSON-call helper.
- Playwright is the approved path for browser execution in this repo.
- Output sinks consume the agent’s ledger outputs rather than an in-loop sink tool.

Acceptance Criteria:
- [ ] A typed shared prospecting module exists with defaults, records, config, runtime-parameter normalization, and memory-store operations.
- [ ] A concrete `GoogleMapsProspectingAgent` exists and follows existing harness patterns.
- [ ] The agent persists progress and qualified leads in durable memory and can resume from memory.
- [ ] The agent emits `qualified_leads` in ledger outputs by default.
- [ ] A Playwright-backed browser integration exists for the shared browser tool surface and supports Google Maps workflow needs.
- [ ] Agent and integration tests pass.

Verification Steps:
- Run targeted agent and integration tests.
- Exercise the memory store directly in tests to confirm persistence and reload behavior.
- Manually inspect ledger outputs for qualified leads structure.

Dependencies:
- Ticket 1.

Drift Guard:
This ticket must not add CLI commands, package/docs/file-index updates beyond what is strictly necessary for the harness module itself, or change the framework-wide sink contract. Keep the work focused on the harness, shared models, and browser integration.
