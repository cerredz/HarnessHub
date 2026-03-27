Title: Integrate dynamic selection into the agent runtime and CLI opt-in flow

Issue URL: https://github.com/cerredz/HarnessHub/issues/389

Intent:
Wire the dynamic selector into the live runtime so agents can opt in without changing the default static path. This ticket also adds the CLI surface for enabling dynamic tooling and selecting candidate existing tools.

Scope:
- Integrate turn-level active-tool selection into `BaseAgent`.
- Preserve the disabled path exactly as current behavior.
- Ensure prompt rendering uses the active turn-level tool set where relevant.
- Add CLI/runtime-config support for enabling dynamic selection and specifying catalog-backed candidate tool keys.
- Add scaffolding so built-in agents can carry the config while remaining disabled by default.

Scope Exclusions:
- No repo-doc generation or public documentation work beyond what is necessary to keep tests passing.
- No blanket opt-in for built-in agents.
- No reranker implementation.

Relevant Files:
- `harnessiq/agents/base/agent.py` — compute active tool set before model request assembly.
- `harnessiq/agents/provider_base/agent.py` — render active tools when dynamic selection is enabled.
- `harnessiq/agents/leads/agent.py` — render active tools when dynamic selection is enabled.
- `harnessiq/shared/agents.py` — any additional helper accessors needed by runtime integration.
- `harnessiq/cli/common.py` — add shared CLI parsing for dynamic tool enablement.
- affected CLI command modules — expose the new flags where appropriate.
- `tests/test_agents_base.py` — verify static path preservation and dynamic path behavior.
- `tests/test_cli_policy_options.py` and CLI-specific tests — verify parsing and config flow.
- targeted agent tests — verify prompt/schema alignment for affected agents.

Approach:
Introduce the notion of an active turn-level tool subset without changing the underlying `tool_executor`.

Runtime flow:
- derive candidate ceiling from current registered tools plus `allowed_tools`
- if dynamic selection is disabled, expose the same tool set as today
- if enabled, resolve candidate profiles and select active keys
- build prompt text and schema exposure from the active set

CLI flow:
- add flags to enable dynamic tooling
- allow users to specify candidate existing tool keys/families by string
- do not attempt to serialize arbitrary Python callables through the CLI

Assumptions:
- Built-in agents remain disabled by default after integration.
- CLI support is for enabling the feature and selecting catalog-backed tools, while custom callable tools remain a Python API concern.
- Empty `allowed_tools` must continue to mean “no explicit ceiling configured.”

Acceptance Criteria:
- [ ] `BaseAgent` preserves current behavior when dynamic selection is disabled.
- [ ] `BaseAgent` can expose an active turn-level subset when dynamic selection is enabled.
- [ ] Prompt/tool rendering stays aligned for affected agents.
- [ ] CLI users can enable dynamic tooling and specify candidate existing tools by string.
- [ ] Built-in agents remain on the static path by default.
- [ ] Integration is covered by runtime, CLI, and targeted agent tests.

Verification Steps:
- Static analysis on changed files.
- Type-check changed files or ensure all new code is annotated.
- Run targeted runtime and CLI unit tests.
- Run affected agent tests for provider-base and leads prompt alignment.
- Run smoke/manual verification of a minimal agent construction path with dynamic selection disabled and enabled.

Dependencies:
- `ticket-1.md`
- `ticket-2.md`

Drift Guard:
This ticket must not redesign the tool registry, replace the approval/allowlist hook, or enable dynamic selection by default for built-in agents. It only adds opt-in runtime integration and CLI enablement.
