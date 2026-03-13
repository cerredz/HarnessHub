Title: Add a provider-agnostic base agent runtime
Intent: Introduce a reusable agent harness layer that can manage prompt assembly, rolling transcripts, tool execution, context resets, and run-loop control without binding the repository to a single model provider or a single agent use case.
Scope:
- Add a new `src/agents/` package with the shared runtime abstractions needed by future agents.
- Define the core model interface, transcript models, context budgeting, and base run loop.
- Reuse the existing tool registry/types rather than inventing a second tool runtime.
- Do not encode LinkedIn-specific memory files, tool catalogs, or prompt rules in this ticket.
Relevant Files:
- `src/agents/base.py`: base runtime abstractions, run loop, transcript handling, and context reset behavior.
- `src/agents/__init__.py`: export the base runtime surface.
- `tests/test_agents_base.py`: cover the generic runtime behavior with fake model and tool collaborators.
Approach: Build the base layer around explicit dataclasses and protocols. The model dependency will be an injected protocol that returns a normalized agent turn containing assistant output, tool calls, and optional control signals. The base agent will own transcript management, sequential tool execution, and context reset by estimated token budget. A max-cycle guard will make the infinite-loop design testable without changing the production semantics.
Assumptions:
- The existing `ToolRegistry` and canonical tool types are the right execution primitive for local harness tools.
- Estimated token counting is sufficient for the initial reset heuristic because the repository does not currently depend on a tokenizer library.
- A provider-agnostic model protocol is preferable to wiring the runtime directly to `OpenAIClient` or another concrete provider.
Acceptance Criteria:
- [ ] A new `src/agents/` package exposes a reusable base agent runtime.
- [ ] The base runtime can build a model request from a system prompt, parameter sections, transcript entries, and tool definitions.
- [ ] The base runtime executes requested tools sequentially and records tool results in the transcript.
- [ ] The base runtime clears and re-injects context when the configured budget threshold is exceeded.
- [ ] The base runtime can stop, continue, or pause deterministically without live provider calls.
- [ ] Unit tests cover the core loop, tool execution, and reset behavior.
Verification Steps:
- Run `python -m unittest tests.test_agents_base`.
- Run `python -m unittest`.
- Smoke-check a fake model plus fake tool registry to confirm the runtime can execute a multi-step loop and pause safely.
Dependencies: None.
Drift Guard: This ticket must not encode LinkedIn-specific files, prompts, or business rules, and it must not introduce provider-specific response parsing. It establishes the agent runtime only.
