Title: Add shared agent tool inspection helpers

Intent: Make it easy to inspect the full tool surface of any Harnessiq agent instance, including descriptions, parameters, required fields, and the backing function metadata, without changing the existing execution contract.

Issue URL: https://github.com/cerredz/HarnessHub/issues/148

Scope:
- Add a shared inspection payload for registered tools in the shared tool/runtime layer.
- Add a registry-level inspection helper that can return stable metadata for all registered tools.
- Add an inherited helper on `BaseAgent` so every concrete agent can expose its tool catalog directly.
- Add or update tests for the shared runtime and representative concrete agents.
- Update `artifacts/file_index.md` to record the new inspection capability.
- Do not change agent execution behavior, provider request translation, or model request tool serialization.

Relevant Files:
- `harnessiq/shared/tools.py`: add stable inspection serialization for a registered tool, including handler identity and parameter metadata.
- `harnessiq/tools/registry.py`: expose registry inspection helpers while preserving execution behavior.
- `harnessiq/shared/agents.py`: keep the executor protocol aligned with the new inspection surface if needed.
- `harnessiq/agents/base/agent.py`: expose the new helper on every agent via the base class.
- `tests/test_tools.py`: verify registry/shared tool inspection payload shape and stability.
- `tests/test_agents_base.py`: verify the base agent helper exposes rich tool metadata.
- `tests/test_knowt_agent.py`: verify a concrete inherited agent exposes the helper as expected.
- `artifacts/file_index.md`: update the architecture artifact.

Approach:
- Preserve `ToolDefinition.as_dict()` as the canonical model-facing representation.
- Add a separate inspection representation at the `RegisteredTool` level so handler metadata stays outside the model request payload.
- Derive parameter metadata from the existing JSON schema instead of inventing a second parameter definition source.
- Expose the new structured payload through `ToolRegistry`, then let `BaseAgent` delegate to the executor when available.
- Keep the new helper additive so existing callers that depend on `available_tools()` continue to work unchanged.

Assumptions:
- Handler identity should be exposed using stable string fields such as module and qualified name.
- Structured inspection output is preferable to only a formatted string because callers can still print or JSON-encode it.
- All in-repo agents use `ToolRegistry`, so the helper will cover all current agents once it is added to `BaseAgent`.

Acceptance Criteria:
- [ ] Every `BaseAgent` subclass inherits a helper that returns rich tool inspection metadata for its configured tools.
- [ ] The inspection payload includes each tool's key, name, description, input schema, required parameters, and handler identity.
- [ ] Existing `available_tools()` behavior remains unchanged.
- [ ] Tool execution and validation behavior remain unchanged.
- [ ] Tests cover the shared inspection payload and at least one concrete inherited agent.
- [ ] `artifacts/file_index.md` documents the new capability.

Verification Steps:
- Run the targeted unit tests for shared tools and agent runtime.
- Run the concrete agent tests impacted by the inherited helper.
- Review the helper output manually from a representative agent instance shape via tests.

Dependencies: None.

Drift Guard:
This ticket must not redesign the tool schema format, replace `available_tools()`, alter provider integrations, or add agent-specific bespoke inspection implementations. The change should stay centralized in the shared tool/runtime layer and expose an additive API only.
