### 1a: Structural Survey

Repository shape relevant to this task:

- `harnessiq/agents/`: shared agent runtime plus concrete agent harnesses.
- `harnessiq/agents/base/agent.py`: `BaseAgent` owns the shared run loop, transcript, context reset behavior, parameter refresh, and the current `available_tools()` accessor.
- `harnessiq/agents/email/agent.py`: abstract email harness built on `BaseAgent`; it derives its system prompt tool list from `available_tools()`.
- `harnessiq/agents/linkedin/agent.py`: concrete LinkedIn harness with internal tool definitions and browser tool definitions merged into a `ToolRegistry`.
- `harnessiq/agents/knowt/agent.py`: concrete Knowt harness that merges reasoning and Knowt tool factories into a `ToolRegistry`.
- `harnessiq/agents/exa_outreach/agent.py`: concrete Exa outreach harness that merges Exa, Resend, and internal tools into a `ToolRegistry`.
- `harnessiq/shared/tools.py`: canonical tool data models. `ToolDefinition` currently carries `key`, `name`, `description`, and `input_schema`. `RegisteredTool` binds the definition to the executable handler.
- `harnessiq/tools/registry.py`: deterministic in-memory registry that stores `RegisteredTool` objects, exposes `definitions()`, and executes handlers with basic schema validation.
- `harnessiq/shared/agents.py`: shared protocol and runtime data models. `AgentToolExecutor` currently only guarantees `definitions()` and `execute()`.
- `tests/test_agents_base.py`: coverage for the generic runtime surface.
- `tests/test_email_agent.py`, `tests/test_linkedin_agent.py`, `tests/test_knowt_agent.py`, `tests/test_exa_outreach_agent.py`: coverage for concrete harness tool wiring.
- `tests/test_tools.py`: coverage for tool metadata serialization and registry behavior.
- `artifacts/file_index.md`: architectural artifact the user explicitly named as an artifact to keep current.

Current architectural behavior:

- Tool metadata exists today in `ToolDefinition`, but only the definition surface is exposed publicly through `ToolRegistry.definitions()` and `BaseAgent.available_tools()`.
- The executable function is stored in `RegisteredTool.handler`, but there is no public inspection helper that exposes that binding in a stable, serialized form.
- All concrete agents in the repository build a `ToolRegistry` and pass it into `BaseAgent`, so a shared enhancement in `ToolRegistry` and `BaseAgent` can cover all current agents without per-agent custom code.
- Existing system prompts often summarize tools manually from `available_tools()`, which suggests any new inspection helper should be additive rather than replacing the current `available_tools()` contract.

Codebase conventions observed:

- Shared runtime behavior is centralized in base classes and shared modules, then inherited by concrete harnesses.
- Public metadata objects expose `as_dict()` helpers that return deep-copied, serialization-safe payloads.
- Tests prefer explicit behavior assertions over introspecting implementation details directly.
- Tool definitions use JSON-schema-like `input_schema` payloads with `properties`, `required`, and `additionalProperties`.

### 1b: Task Cross-Reference

User request mapping:

- "add this functionalities to the agent base class and all agents":
  This maps primarily to `harnessiq/agents/base/agent.py`, because all concrete agents inherit from `BaseAgent`.
- "i want it to be very easy to 'see' the tools that an agent has":
  The current closest surface is `BaseAgent.available_tools()`, but it returns only `ToolDefinition` objects. The missing piece is a richer inspection helper that packages those definitions in a directly consumable form.
- "each agent should have a helper function that lets me do this":
  The most coherent implementation is a new helper method on `BaseAgent`, inherited automatically by all concrete agents (`BaseEmailAgent`, `KnowtAgent`, `LinkedInJobApplierAgent`, `ExaOutreachAgent`).
- "see all tool descriptions, parameters, function, etc":
  Relevant source of truth is split between `ToolDefinition` (`description`, `input_schema`) and `RegisteredTool` (`handler`). The task therefore touches `harnessiq/shared/tools.py` and `harnessiq/tools/registry.py` in addition to `BaseAgent`.
- "Artifact: artifacts\\file_index.md":
  The file index should be updated to mention the new shared inspection capability in the agent/tool runtime layer.

Likely code touch points:

- `harnessiq/shared/tools.py`: add a stable inspection payload for registered tools, including handler identity and parameter metadata derived from `input_schema`.
- `harnessiq/tools/registry.py`: expose a registry-level helper that returns inspection payloads for all or selected tools.
- `harnessiq/shared/agents.py`: optionally widen the `AgentToolExecutor` protocol if the new shared helper should be part of the formal executor contract.
- `harnessiq/agents/base/agent.py`: add the new agent-level helper so every agent instance can surface rich tool metadata.
- Tests in `tests/test_agents_base.py`, `tests/test_tools.py`, and at least one concrete agent test module to confirm inheritance and output shape.
- `artifacts/file_index.md`: record the new capability.

Behavior that must be preserved:

- `BaseAgent.available_tools()` must remain intact for existing callers and system prompt construction.
- `AgentModelRequest.estimated_tokens()` should continue to serialize only canonical tool definitions, not handler internals.
- Tool execution and validation paths in `ToolRegistry.execute()` must remain unchanged.
- Concrete agent constructors and tool wiring order must remain unchanged.

Blast radius:

- Low to moderate. The change is centered in shared metadata and agent inspection surfaces, but those surfaces are used across the SDK. Backward compatibility matters more than raw implementation size.

### 1c: Assumption & Risk Inventory

Assumptions:

- The user wants an inherited helper on `BaseAgent`, not unique custom helpers on each concrete agent class.
- "function" means the callable backing each tool, best represented as module and qualified function name rather than a raw Python object repr.
- A structured inspection payload is more useful than only a human-formatted string, because callers can print it, log it, or build UIs from it.
- Existing callers depend on `available_tools()` returning `ToolDefinition` objects, so the new feature must be additive.

Risks:

- If the inspection helper exposes raw handler repr strings, the output could be unstable across runs and hard to test. Prefer stable module and qualname fields.
- If `ToolDefinition.as_dict()` is changed to include handler details, model request token estimation and provider integrations would be altered. Avoid that by creating a separate inspection payload.
- If the `AgentToolExecutor` protocol is made stricter, external custom executors could become type-incompatible. A graceful fallback or additive protocol change is safer than replacing the existing contract.
- The repository has a dirty worktree with unrelated changes. Implementation must avoid touching or reverting user work outside the scoped files.

Phase 1 complete.
