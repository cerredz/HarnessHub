Title: Resolve the PR #382 prompt-harness review follow-ups
Issue URL: https://github.com/cerredz/HarnessHub/issues/394

Intent:
Implement the architectural and behavior changes requested in the inline review comments on PR #382 so the new prompt-driven harnesses conform to repository standards, persist richer durable mission state, and stop duplicating file-backed agent initialization logic.

Scope:
- Refactor shared file-backed agent setup into `BaseAgent` support that mission-driven and spawn-specialized-subagents can both use.
- Move prompt-harness registered tool definitions/factories into `harnessiq/tools/`.
- Replace stage subcalls that reuse the full bundled master prompts with stage-specific prompts.
- Expand the mission-driven durable artifact model and tool interactions to cover the additional records requested in review.
- Ensure default mission-driven instances create isolated memory subfolders when the caller omits `memory_path`.
- Update or add tests needed to verify the new shared initialization path, durable records, and default-memory behavior.
- Do not redesign unrelated agent families beyond the minimum needed to keep the new shared base behavior coherent.

Relevant Files:
- `harnessiq/agents/base/agent.py`: add reusable file-backed initialization helpers and any memory-path support needed by the new harnesses.
- `harnessiq/agents/helpers.py`: add or adjust default-memory resolution helpers for isolated per-run subfolders.
- `harnessiq/agents/mission_driven/agent.py`: adopt the shared base-agent initialization path and use tool-layer factories.
- `harnessiq/agents/spawn_specialized_subagents/agent.py`: adopt the shared base-agent initialization path and use tool-layer factories.
- `harnessiq/agents/mission_driven/stages.py`: replace full-master-prompt subcall prompts with artifact-specific prompts.
- `harnessiq/agents/spawn_specialized_subagents/stages.py`: replace full-master-prompt subcall prompts with artifact-specific prompts.
- `harnessiq/shared/mission_driven.py`: expand durable mission records and supporting memory-store APIs.
- `harnessiq/tools/mission_driven/*`: add reusable mission-driven tool definitions/factories.
- `harnessiq/tools/spawn_specialized_subagents/*`: add reusable spawn-specialized-subagents tool definitions/factories.
- `tests/test_mission_driven_agent.py`: verify richer durable records, tool behavior, and default memory isolation.
- `tests/test_spawn_specialized_subagents_agent.py`: verify the harness still exposes and executes the delegated tooling after the tool-layer move.
- `tests/test_agents_base.py`: cover the new shared file-backed base-agent helper behavior if needed.

Approach:
Refactor around a single post-resolution initialization path in `BaseAgent` for file-backed agents that persist runtime/custom/additional-prompt state. The prompt harnesses should stop writing their store twice and should instead rely on a shared helper that prepares the resolved store after instance registration. Tool definitions should move into `harnessiq/tools/` with injected handlers so the agent classes remain orchestration layers. Mission-driven stages should use narrow artifact-specific prompts derived from the contract of each stage, and the mission memory store should gain the additional durable logs and queue surfaces that the review requested.

Assumptions:
- The required architectural scope is limited to the prompt harnesses plus the shared base support they rely on.
- Existing public tool keys in `harnessiq/shared/tools.py` remain authoritative and should not be renamed.
- Default-memory isolation should apply only when `memory_path` is omitted; explicit memory paths should continue to opt into resumable reuse.

Acceptance Criteria:
- [ ] The prompt harness constructors no longer duplicate file-backed store preparation/writes that are now handled through a shared `BaseAgent` path.
- [ ] Mission-driven and spawn-specialized-subagents registered tool definitions live under `harnessiq/tools/` instead of inline in agent classes.
- [ ] Mission-driven and spawn-specialized-subagents stage subcalls use stage-specific prompts rather than the full original master prompt text plus a short suffix.
- [ ] The mission-driven memory store persists the additional review-requested durable records and the agent exposes tool behavior that updates them.
- [ ] Default mission-driven construction without `memory_path` creates an isolated subfolder instead of reusing one shared artifact directory.
- [ ] Focused tests for the prompt harnesses and any affected base-agent behavior pass.

Verification Steps:
- Run `python -m pytest tests/test_mission_driven_agent.py tests/test_spawn_specialized_subagents_agent.py tests/test_agents_base.py`.
- Run `python -m compileall harnessiq tests`.
- Manually inspect the mission-driven and spawn-specialized-subagents tool definitions through the public agent surface to confirm the tool keys stay stable and are sourced from the tooling layer.
- Manually instantiate `MissionDrivenAgent` twice without `memory_path` in a focused test and confirm the resolved directories do not collide.

Dependencies:
- None.

Drift Guard:
This ticket must stay focused on the PR #382 review comments. It must not redesign unrelated harness behavior, rename public tool keys, or broaden the refactor into every agent in the repo beyond the minimum shared base support required to make the new prompt harnesses correct and maintainable.
