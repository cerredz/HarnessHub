Title: Add the ResearchSweepAgent harness to the SDK and CLI

Issue URL:
https://github.com/cerredz/HarnessHub/issues/252

Intent:
Introduce the design-doc-defined academic research sweep harness as a first-class built-in Harnessiq harness. The result should be usable from the SDK, discoverable through the manifest-driven platform CLI, available through a direct `research-sweep` command family, and covered by tests and generated repo docs.

Scope:
- Add a new built-in `research_sweep` harness manifest in the shared manifest registry.
- Add the `ResearchSweepAgent` implementation with the required Serper/context tool surface, durable reset-safe state handling, report/error outputs, and SDK exports.
- Add a shared research sweep memory/config module and a CLI adapter for the platform-first CLI.
- Add a direct top-level `research-sweep` CLI with `prepare`, `configure`, `show`, and `run`.
- Add or update tests for manifests, agent behavior, CLI behavior, packaging, and generated docs as needed.
- Regenerate the generated README and artifact docs.

Scope Exclusions:
- Do not redesign the generic context-tool APIs beyond what is required for this harness to use a restricted subset safely.
- Do not add new external providers or bypass the existing Serper provider/tool stack with raw HTTP logic.
- Do not refactor unrelated harnesses or normalize existing CLI inconsistencies outside the blast radius of this feature.
- Do not merge the PR; the task ends at a created PR targeting `main`.

Relevant Files:
- `harnessiq/shared/research_sweep.py`: shared defaults, config, memory-store helpers, manifest, and normalization helpers for the new harness.
- `harnessiq/shared/__init__.py`: export the new manifest and helpers as needed.
- `harnessiq/shared/harness_manifests.py`: register the new built-in manifest.
- `harnessiq/agents/research_sweep/__init__.py`: export the concrete agent.
- `harnessiq/agents/research_sweep/agent.py`: implement the `ResearchSweepAgent`.
- `harnessiq/agents/research_sweep/prompts/master_prompt.md`: store the static research sweep prompt text if prompt-file loading is used.
- `harnessiq/agents/__init__.py`: export the new agent from the SDK package.
- `harnessiq/cli/adapters/research_sweep.py`: platform CLI adapter for the new harness.
- `harnessiq/cli/research_sweep/__init__.py`: direct CLI package export.
- `harnessiq/cli/research_sweep/commands.py`: direct `research-sweep` command family.
- `harnessiq/cli/main.py`: register the new top-level CLI family.
- `tests/test_research_sweep_agent.py`: unit coverage for the agent’s durable state, outputs, and tool surface.
- `tests/test_research_sweep_cli.py`: CLI coverage for parser registration and direct command behavior.
- `tests/test_platform_cli.py`: platform CLI coverage for the new manifest-driven harness.
- `tests/test_harness_manifests.py`: manifest-registry coverage for the new harness.
- `tests/test_sdk_package.py`: SDK/package export coverage if needed for the new agent.
- `README.md`: generated docs update after adding the new harness.
- `artifacts/commands.md`: generated CLI catalog update.
- `artifacts/file_index.md`: generated architecture index update.
- `artifacts/live_inventory.json`: generated inventory update.
- `scripts/sync_repo_docs.py`: not expected to change, but it is part of the verification pipeline because generated docs must stay in sync.

Approach:
Implement the harness as a concrete `BaseAgent` subclass that composes a deterministic tool registry from Serper plus a filtered subset of context tools. Use BaseAgent’s durable context runtime state as the backing store for the sweep-progress schema, but override parameter-section composition so the context window presents a `Research Sweep Memory` section matching the design doc rather than the generic `Context Memory` label. Keep typed harness metadata in the shared manifest layer and add both CLI surfaces: a platform adapter driven by manifest/profile/credential bindings and a direct `research-sweep` command family backed by a small native memory/config store for ergonomic `configure/show/run` flows. Verify behavior with stubbed models and Serper clients so tests cover durable state transitions, final report/error generation, CLI wiring, and generated doc sync without relying on live network calls.

Assumptions:
- A single ticket and single PR are acceptable for this feature because the user asked for one end-to-end integration and the skill’s dependent-ticket merge workflow would otherwise block completion.
- The platform-first CLI should use the existing `serper` provider credential binding flow instead of storing raw API keys as custom parameters.
- The direct top-level CLI can be named `research-sweep` while the manifest id remains `research_sweep`, following existing repo naming patterns.
- It is acceptable to realize the design doc’s restricted context-tool surface by filtering the existing context tool family rather than changing the public `create_context_tools()` signature.
- Tests may validate reset-safety via stubbed model/tool interactions and durable-state assertions rather than full token-threshold simulations.

Acceptance Criteria:
- [ ] The shared manifest registry contains a built-in `research_sweep` harness with typed runtime/custom parameters, declared memory entries, provider families, and output schema.
- [ ] The SDK exports a concrete `ResearchSweepAgent` that can be imported from `harnessiq.agents`.
- [ ] The agent uses the Serper provider/tool stack plus only the required context tool subset and persists sweep state durably across resets.
- [ ] The agent exposes a `Research Sweep Memory` parameter section with the documented schema and emits either a final Markdown report or a structured no-results error block.
- [ ] The platform-first CLI exposes the new harness under `prepare/show/run/inspect/credentials`.
- [ ] A direct `harnessiq research-sweep` CLI family exists with `prepare`, `configure`, `show`, and `run`.
- [ ] Automated tests cover the new harness registration, direct CLI, platform CLI integration, and core agent behavior.
- [ ] Generated docs are regenerated and the docs sync check passes.
- [ ] The feature is pushed on a dedicated branch and a PR targeting `main` is created.

Verification Steps:
1. Static analysis: run the project’s available Python static checks or, if no dedicated linter is configured, use targeted compilation plus style review on changed files.
2. Type checking: run any configured type checker if present; otherwise ensure new Python code is fully type-annotated and `python -m compileall harnessiq tests` passes for the changed modules.
3. Unit tests: run focused tests for the new harness, manifest registry, CLI surfaces, packaging exports, and doc sync.
4. Integration and contract tests: run the broader platform CLI/manifests/docs sync tests that exercise the new registration path and generated artifact contract.
5. Smoke verification: use the CLI parsers and command handlers with stub factories to confirm the direct and platform CLI surfaces produce the expected JSON and register the expected subcommands.

Dependencies:
- None.

Drift Guard:
This ticket must remain narrowly focused on introducing the research sweep harness as a new first-class built-in harness. It must not become a generic context-tool redesign, a credential-system rewrite, or a cleanup pass over unrelated harnesses. Any reusable helper added for this harness must stay justified by the new integration path and must not widen scope into speculative abstractions that are not required to ship the research sweep feature cleanly.
