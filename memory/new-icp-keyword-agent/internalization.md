### 1a: Structural Survey

Repository shape:

- `harnessiq/` is the shipped SDK package. It is organized around agent harnesses, shared runtime/data models, CLI entrypoints, provider-backed tools, integrations, and utilities.
- `harnessiq/agents/` contains the abstract runtime (`base/agent.py`) plus concrete harnesses:
  - `linkedin/agent.py`: the strongest example of a durable-memory browser agent with CLI-backed persisted configuration and injectable browser runtime handlers.
  - `exa_outreach/agent.py`: the strongest example of deterministic event logging into JSON run files plus internal tool handlers that persist leads/emails regardless of model behavior.
  - `knowt/agent.py` and `email/agent.py`: narrower examples of prompt-driven harnesses built on the same `BaseAgent`.
- `harnessiq/shared/` contains dataclasses, config normalization, filenames, and memory-store helpers that concrete agents depend on. `shared/exa_outreach.py` and `shared/linkedin.py` are the closest patterns for this task.
- `harnessiq/cli/` contains the root argparse entrypoint plus agent-specific command modules. Each concrete agent has its own command registration module and typically supports `prepare`, `configure`, `show`, and `run`.
- `harnessiq/integrations/` contains runtime bridges such as the Playwright-backed LinkedIn browser session and model adapters. Browser automation is not global today; it is injected per agent through integration code.
- `harnessiq/tools/` and `harnessiq/toolset/` provide the deterministic tool runtime layer. `ToolRegistry` is the canonical in-memory execution/validation surface for local tools.
- `harnessiq/utils/` contains reusable persistence helpers including agent-instance resolution (`agent_instances.py`) and run-event storage (`run_storage.py`).
- `tests/` is broad and mostly unit-style. Existing test coverage asserts SDK exports, CLI registration, agent parameter ordering, memory persistence, and tool behavior.
- `docs/` and `README.md` describe the public runtime and CLI contracts and are expected to be kept in sync with new agent surfaces.
- `artifacts/file_index.md` is the architectural reference for top-level layout and conventions.

Technology and runtime conventions:

- Language/runtime: Python 3.11+, setuptools packaging, pytest/unittest mixed test suite.
- Agent architecture: concrete agents inherit `BaseAgent`, implement `build_system_prompt()` and `load_parameter_sections()`, optionally `prepare()`, and usually inject a `ToolRegistry`.
- Context-window ordering is fixed by `BaseAgent`: system prompt, then parameter sections in the order returned by `load_parameter_sections()`, then transcript entries.
- Durable memory is file-backed under a per-agent memory folder. CLI flows typically persist configuration to files and reconstruct runtime state through a memory-store abstraction.
- Deterministic persistence is preferred when model recall would be lossy. `ExaOutreachAgent` logs events inside tool handlers; `LinkedInJobApplierAgent` persists append-only records plus recent semantic actions.
- Browser automation is currently agent-specific. `integrations/linkedin_playwright.py` owns session lifecycle and tool handlers and uses persistent browser profiles under agent memory.
- Packaging/public surface is curated explicitly through `harnessiq/__init__.py`, `harnessiq/agents/__init__.py`, CLI command registration, and tests like `tests/test_sdk_package.py`.

Observed conventions and relevant inconsistencies:

- Agent-specific shared models live in `harnessiq/shared/<domain>.py`; agent package `__init__.py` files re-export the concrete harness.
- CLI naming is domain-based (`linkedin`, `outreach`), not class-name based.
- Browser tooling is exposed as concrete tool definitions plus a separate integration that wires runtime handlers; there is no general reusable browser abstraction yet.
- `BaseAgent` only refreshes parameter sections at start/reset. If a task requires parameter sections to reflect newly persisted state during an active run, the concrete agent must explicitly refresh after tool execution or use compaction.
- The repository is currently in a dirty state with many unrelated tracked and untracked changes, so this task must avoid broad refactors or cleanup outside its own blast radius.

### 1b: Task Cross-Reference

User request, mapped to codebase:

1. "Create a new agent ... input should be a list of descriptions of ICPs"
- Requires a new concrete harness under `harnessiq/agents/`.
- Requires a new shared memory/config module under `harnessiq/shared/`.
- Requires CLI configure/show/run commands to persist and reload ICP lists.

2. "come up with keywords for the search"
- The new harness system prompt and tool surface must steer the model to derive keywords from persisted ICP descriptions.
- For determinism, the actual search execution should be handled by code, not by free-form browser manipulation alone.

3. "more deterministic"
- Strongly points to the `ExaOutreachAgent` pattern: high-level deterministic tool handlers that perform persistence immediately.
- Also points to a narrow browser/search integration rather than exposing a wide browser tool surface and hoping the model uses it consistently.

4. "context window should be the system prompt, icp, then recent searches"
- Requires `load_parameter_sections()` to order sections as ICPs first, recent searches second.
- Because `BaseAgent` always appends transcript after parameter sections, the authoritative durable ordering can be satisfied, but a concrete agent may need to refresh sections after search tools run.

5. "After it searches and gets results, the context window should be the same with the appended search results"
- Requires an additional parameter section for recent/persisted search results.
- Because `BaseAgent` does not automatically reload parameters after every tool call, the new agent likely needs a targeted override around tool execution to call `refresh_parameters()` after memory-mutating tools complete.

6. "The leads/emails that it finds should be stored in its memory in a json file"
- Requires a durable JSON memory file for canonical leads/emails, likely alongside agent config files.
- `harnessiq/utils/run_storage.py` is relevant if per-run JSON event logs are also desirable, but the user specifically asked for persistent JSON memory, so a top-level canonical JSON file is needed.

7. "Make sure that when the agent loads the browser/tabs the content is fully loaded"
- Requires a new Playwright-backed integration under `harnessiq/integrations/`.
- Existing reference: `integrations/linkedin_playwright.py`, especially its session lifecycle and page interaction patterns.
- The new integration should explicitly wait for load completion for both the search results page and opened result tabs/pages.

8. "functions to get emails exposed in the sdk/cli after the user runs the agent"
- Requires SDK-level methods on the agent and/or memory store, plus public exports in `harnessiq/agents/__init__.py`.
- Requires CLI commands, likely a new `get-emails` subcommand under the new agent domain.

9. "emails gotten should persist after running the agent in its memory"
- Requires the CLI `run` path to use the persisted memory folder and not transient in-memory state.
- Favors a `from_memory(...)` constructor pattern similar to `LinkedInJobApplierAgent`.

10. "build this agent into the sdk and cli of our repo"
- Requires updating:
  - `harnessiq/agents/`
  - `harnessiq/cli/main.py`
  - agent/domain-specific CLI package
  - `harnessiq/__init__.py` or other public export points if needed
  - README/docs/tests

11. "replicate ... just the instagram keyword part"
- Scope is limited to: derive keyword(s), execute Google `site:instagram.com`-style searches, extract emails from discovered pages/content, and persist them.
- Out of scope unless later requested: email verification, sending, campaign orchestration, pricing negotiation, attribution/tracking, or ad-spend logic.

Primary files/modules likely affected:

- New:
  - `harnessiq/agents/<new_agent>/__init__.py`
  - `harnessiq/agents/<new_agent>/agent.py`
  - `harnessiq/agents/<new_agent>/prompts/master_prompt.md`
  - `harnessiq/shared/<new_agent>.py`
  - `harnessiq/cli/<new_agent>/__init__.py`
  - `harnessiq/cli/<new_agent>/commands.py`
  - `harnessiq/integrations/<new_agent>_playwright.py`
  - `tests/test_<new_agent>_agent.py`
  - `tests/test_<new_agent>_cli.py`
- Existing:
  - `harnessiq/agents/__init__.py`
  - `harnessiq/cli/main.py`
  - `harnessiq/shared/tools.py` if new internal tool-key constants are added
  - `harnessiq/__init__.py` only if top-level export policy changes
  - `README.md`
  - `artifacts/file_index.md`
  - potentially `tests/test_sdk_package.py`

Blast radius:

- Moderate. This is a net-new agent plus CLI command and integration, but it touches core package exports and public docs.
- The cleanest implementation path is additive and should avoid modifying unrelated existing agent behavior.

### 1c: Assumption & Risk Inventory

Assumptions I can likely resolve locally:

- The new agent should follow existing domain-command naming conventions, so a new root CLI namespace is appropriate rather than overloading `outreach`.
- The ICP input can be stored as a persisted list of strings in the agent memory folder.
- The "get emails" surface should read from persisted memory, not from the last in-process run object only.
- "Just the instagram keyword part" excludes the downstream verification/email-sending workflow.

Material implementation risks:

- Search backend ambiguity: the request references Google search syntax and browser tabs, but the repo has no existing generic Google-search browser harness. A new Playwright integration is required and must be designed carefully to avoid a brittle wide-open browser tool surface.
- Context refresh gap: `BaseAgent` does not automatically reload parameter sections after tool handlers mutate memory. Without a deliberate refresh step, appended search results would not appear in parameter sections until a reset or next run.
- Load-state correctness: Playwright `goto()` completion alone is not enough for the user requirement. The integration must explicitly wait for the document and any opened result tabs to be fully usable before extraction.
- Output-shape ambiguity: the user asked for "leads/emails" in JSON memory. The exact schema is not predefined in the repo, so the new shared module must define one that supports dedupe, provenance, and retrieval cleanly.
- SDK/CLI persistence contract: if the new CLI `run` path reconstructs the agent incorrectly, emails may persist in run-local files but not in the canonical memory JSON required by the user.
- Dirty worktree risk: several core files already contain unrelated changes. Touch points like `harnessiq/agents/__init__.py`, `harnessiq/__init__.py`, and `README.md` need careful read-modify-write edits to avoid clobbering existing user work.
- GitHub issue / PR workflow risk from the requested skill: the skill mandates `gh` issue/PR creation, but this environment has restricted network access, so those steps may be impossible to complete locally even if the code work is completed.

Open design choices I may still need to lock down before implementation:

- Final agent/domain naming (`instagram`, `instagram_keyword`, `instagram_leads`, etc.).
- Whether CLI ICP input should be repeated `--icp` flags, JSON file import, or both.
- Whether `get-emails` should default to all persisted unique emails or expose both all-time and per-run modes.
- Whether canonical persisted state should be a single JSON file or a small set of JSON files (preferred for clarity if the schema is non-trivial).

Phase 1 complete.
