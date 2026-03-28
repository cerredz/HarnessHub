## PR 382 Review Follow-Ups Internalization

### 1a: Structural Survey

#### Repository shape

- `harnessiq/` is the live runtime package. `artifacts/file_index.md` explicitly marks it as the only authoritative source tree and says tooling/provider behavior belongs in `harnessiq/tools/`, `harnessiq/providers/`, and `harnessiq/agents/`.
- `harnessiq/agents/base/agent.py` is the shared agent runtime. It resolves instance identity and memory paths through `AgentInstanceStore`, owns the run loop, tool execution, transcript lifecycle, and ledger output.
- `harnessiq/agents/helpers.py` is the current lightweight helper layer for repo-root and memory-path resolution. It currently returns the raw default path when `memory_path` is omitted.
- `harnessiq/shared/` holds cross-cutting runtime contracts: harness manifests, DTOs, validated types, and the shared tool-key catalog in `harnessiq/shared/tools.py`.
- `harnessiq/tools/` is the canonical execution layer. Existing families such as `instagram`, `knowt`, `leads`, and `context` expose tool factories and definitions there rather than embedding tool definitions inside agent classes.
- `harnessiq/utils/agent_instances.py` is the instance-registry layer. Its default behavior creates per-instance directories under `memory/agents/<agent>/<instance-dir>`, but only when the caller does not pass an explicit memory path into `BaseAgent`.
- `tests/` is the primary verification surface. The new prompt harnesses are covered by `tests/test_mission_driven_agent.py`, `tests/test_spawn_specialized_subagents_agent.py`, and manifest coverage in `tests/test_harness_manifests.py`.

#### Relevant architecture

- `MissionDrivenAgent` and `SpawnSpecializedSubagentsAgent` both perform substantial constructor work before and after `super().__init__()`: they resolve a memory path, instantiate a file-backed store, prepare it, write runtime/custom/additional-prompt files, build a tool registry, call `BaseAgent`, then rebuild the store against the resolved `self.memory_path`.
- Other agents show the same pattern in different forms. `ResearchSweepAgent` writes configuration files before and after `super().__init__()`. `KnowtAgent` and `InstagramKeywordDiscoveryAgent` build tool handlers against a store before `BaseAgent` has finalized the instance path, which makes constructor behavior inconsistent across the codebase.
- The PR #382 harnesses currently define their own internal `RegisteredTool` objects inline in agent classes even though the repo standard in the file index says tools should live in the tooling layer.
- The staged model subcalls for both harnesses currently reuse the full bundled master prompt plus short stage-contract text. The review explicitly rejects that approach and asks for stage-specific prompts that are scoped to the artifact each stage produces.
- `MissionDrivenMemoryStore` already persists `mission.json`, `task_plan.json`, `memory_store.json`, `decision_log.json`, `file_manifest.json`, `error_log.json`, `feedback_log.json`, `test_results.json`, `artifacts.json`, `progress_log.jsonl`, `README.md`, and checkpoints. Review comments require additional durable records and tool/LLM interactions around them.

#### Conventions and constraints

- Follow the file index: agent classes orchestrate, tools execute deterministic operations, and provider-backed or reusable surfaces should land under `harnessiq/tools/` rather than as ad hoc inline runtime definitions.
- Runtime configuration is normalized through manifest and DTO layers, and tests expect deterministic JSON-friendly outputs from tool handlers and model subcalls.
- The repository already carries many `memory/` task artifacts. This branch must preserve that pattern by writing all planning artifacts under `memory/pr-382-review-followups/`.
- The root checkout is dirty on a different feature branch, so all implementation work must remain confined to this worktree and must not reset or overwrite the user's existing local state.

### 1b: Task Cross-Reference

User task: inspect the comments left on GitHub PR #382, adhere to `artifacts/file_index.md`, and implement the requested changes now that PR #382 is already merged to `main`.

Concrete mapping of the actionable PR comments:

1. Move overlapping constructor logic into the abstract base agent class.
   - Primary targets: `harnessiq/agents/base/agent.py`, `harnessiq/agents/helpers.py`, `harnessiq/agents/mission_driven/agent.py`, `harnessiq/agents/spawn_specialized_subagents/agent.py`
   - Adjacent comparison files: `harnessiq/agents/research_sweep/agent.py`, `harnessiq/agents/knowt/agent.py`, `harnessiq/agents/instagram/agent.py`, `harnessiq/agents/leads/agent.py`
   - Desired outcome: a reusable base-level pattern for file-backed agent initialization and config persistence so new harnesses do not duplicate store preparation and runtime/custom/additional-prompt writes.

2. Expand the mission-driven durable record model and add tool/LLM support for it.
   - Primary targets: `harnessiq/shared/mission_driven.py`, `harnessiq/agents/mission_driven/agent.py`, `harnessiq/agents/mission_driven/stages.py`
   - Needed additions from review: tool-call history record, richer file-manifest structure, richer decision-log sub-artifacts, next-action queue, research log, and explicit mission-status handling.
   - Verification surface: `tests/test_mission_driven_agent.py`

3. Replace stage prompts that reuse the full master prompt with stage-specific prompts.
   - Targets: `harnessiq/agents/mission_driven/stages.py`, `harnessiq/agents/spawn_specialized_subagents/stages.py`
   - Supporting source: bundled master prompts in `harnessiq/master_prompts/prompts/mission_driven.json` and `harnessiq/master_prompts/prompts/spawn_specialized_subagents.json`
   - Desired outcome: each stage should use a narrow system prompt for its own artifact instead of concatenating the entire original prompt plus a short contract blurb.

4. Move the prompt-harness registered tools into the tooling layer.
   - Targets: new reusable tool factories under `harnessiq/tools/`, plus `harnessiq/agents/mission_driven/agent.py` and `harnessiq/agents/spawn_specialized_subagents/agent.py`
   - Shared constants stay in `harnessiq/shared/tools.py`
   - Verification surface: tests for both harness agents should continue to assert tool availability and behavior via the public tool keys.

5. Ensure default mission-driven runs create isolated subfolders automatically when the caller omits `memory_path`.
   - Primary targets: `harnessiq/agents/helpers.py`, `harnessiq/agents/base/agent.py`, `harnessiq/agents/mission_driven/agent.py`
   - Cross-check with current instance behavior: `harnessiq/utils/agent_instances.py`
   - Desired outcome: default runs should never reuse one shared mission artifact directory just because no path was provided.

Behavior that must be preserved:

- Existing public tool keys for mission-driven and spawn-specialized-subagents remain stable because tests and bundled prompts refer to them.
- `BaseAgent` continues to own instance registration, run-loop orchestration, and runtime bookkeeping.
- Harness manifests and DTO payloads remain valid and should still reflect resolved runtime configuration.
- Existing tests for the new harnesses continue to pass after the refactor, with new assertions added only where the review comments require stronger behavior guarantees.

### 1c: Assumption & Risk Inventory

#### Assumptions

- The six inline PR comments returned by `gh api repos/cerredz/HarnessHub/pulls/382/comments --paginate` are the full requested scope for this follow-up.
- The review request to move overlapping constructor logic into `BaseAgent` is architectural guidance, not a demand to make every agent identical; the correct target is the reusable file-backed agent initialization path shared by agents that persist runtime/custom/additional-prompt state.
- The tooling-layer request applies to both prompt harnesses, even though one inline comment was attached specifically to `SpawnSpecializedSubagentsAgent`.
- Stage-specific prompts can live in Python for now if they are narrow and deterministic; the critical requirement is that they no longer reuse the full original master prompt verbatim.

#### Risks

- Refactoring `BaseAgent` constructor support incorrectly could break agent instance registration or widen the blast radius into unrelated harnesses.
- Several pre-existing agents already mix pre-`super()` and post-`super()` store initialization differently; tightening the shared pattern may expose latent path-resolution bugs in those constructors.
- Expanding the mission artifact model without matching tests can create a superficially richer store that the agent never actually updates through tool calls.
- Moving tool definitions into `harnessiq/tools/` can create circular imports if agent classes and tool factories depend on each other directly instead of through injected handlers.
- Default-memory isolation has two layers in this repo: helper-level path resolution and `AgentInstanceStore`. The fix must not accidentally remove resumability for explicit memory paths.

#### Clarification status

- No blocking ambiguities remain. The review comments are concrete enough to implement directly.

Phase 1 complete.
