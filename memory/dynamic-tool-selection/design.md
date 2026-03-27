# Dynamic Tool Selection
## HarnessHub / harnessiq

**Status:** Proposal  
**Location:** `memory/dynamic-tool-selection/design.md`  
**Intent:** Add an optional dynamic tool-selection layer on top of the existing static tool-registration path without changing the default agent behavior.

---

## 1. Core Principle

The default tool delivery path in `harnessiq` does not change.

Agents that do not explicitly opt in to dynamic tool selection should continue to behave exactly as they do today:

- they construct a runtime `tool_executor`
- they expose all registered tool definitions from that executor to the model on each turn
- they still rely on `allowed_tools` as the execution ceiling enforced by the approval/allowlist hook

Dynamic tool selection is an optional per-agent layer for agents whose registered tool surface is large enough that per-turn narrowing is worth the extra machinery.

The governing rule is:

> Registered tools = what the runtime can execute and, by default, what the model sees.  
> `allowed_tools` = the execution ceiling and policy guard.  
> Dynamic selection = an optional per-turn narrowing of the model-visible tool set inside that ceiling.

This selector grants no new authority. It only reduces the tool set exposed to the model for a given turn. The existing policy gate in `harnessiq/tools/hooks/defaults.py` remains authoritative for execution.

---

## 2. Problem Statement

Today, `BaseAgent.build_model_request()` builds an `AgentModelRequest` with `tools=self.available_tools()`. `available_tools()` returns every tool definition exposed by the agent's `tool_executor`.

This is the correct default for small tool surfaces. It becomes expensive or noisy when an agent accumulates many registered tools across multiple functional phases.

Primary failure modes:

- Tool schema tokens consume context that could otherwise hold transcript state, parameter sections, or recent tool results.
- The model has to reason over too many similar schemas at once, which increases tool-selection noise.
- Prompts that render tool lists become bloated and less phase-aware.
- Large multi-family agents may expose tools that are technically valid but irrelevant for the current step, which increases "contact rot" in the tool layer.

Current repository constraints that matter:

- `harnessiq/agents/base/agent.py` is the shared runtime loop and current model-request assembly point.
- `harnessiq/shared/agents.py` owns `AgentRuntimeConfig` and shared runtime models.
- `harnessiq/interfaces/` is the established home for dependency-seam protocols.
- `harnessiq/toolset/` owns static catalog metadata and lookup helpers.
- `harnessiq/tools/` owns executable tool runtime surfaces, not abstract selection policy.

That means the dynamic layer should be modeled as an interface-backed runtime dependency, not as a new executable tool family.

---

## 3. Design Goal

Add an optional dynamic tool-selection layer that can be enabled per agent.

When disabled:

- behavior is unchanged
- no selector is instantiated
- no embedding work is done
- no extra latency is added

When enabled:

- the selector receives the current turn context
- it narrows the model-visible tool set to a smaller active subset
- the selected set is always a subset of the agent's registered tools and a subset of the `allowed_tools` ceiling when a ceiling is provided
- execution still flows through the existing hook-based allowlist gate

---

## 4. Architectural Shape

The feature is built from four concepts:

- `DynamicToolSelector`
- `ToolProfile`
- `ToolSelectionConfig`
- `ToolSelectionResult`

Constraint from implementation scoping:

- this feature is built on top of the existing tool catalog
- the existing catalog model and lookup semantics should remain intact
- dynamic selection introduces a parallel retrieval-profile layer rather than redefining the catalog itself

The key repository-specific change from the earlier draft is placement:

- the selector contract belongs in `harnessiq/interfaces/`
- the shared value objects belong in `harnessiq/shared/`
- the concrete default implementation belongs behind the interface, ideally under `harnessiq/toolset/` because this layer depends on catalog metadata and selection over tool definitions, not on executable tool behavior

Recommended package layout:

- `harnessiq/interfaces/tool_selection.py`
  - `DynamicToolSelector`
  - optional `EmbeddingBackend` protocol
- `harnessiq/shared/tool_selection.py`
  - `ToolProfile`
  - `ToolSelectionConfig`
  - `ToolSelectionResult`
- `harnessiq/toolset/dynamic_selector.py`
  - default cosine-similarity selector implementation
  - index-building logic
  - optional reranking hooks in later versions
- `harnessiq/providers/...`
  - provider-backed embedding client surface used by the default selector backend

This keeps the boundary aligned with the file index:

- `interfaces/` owns seams
- `shared/` owns runtime dataclasses
- `toolset/` owns catalog and lookup concerns
- `tools/` continues to own executable tool families only

---

## 5. Interface-First Contract

The selector should be defined as a protocol first, so `BaseAgent` depends on the abstraction and not on any concrete retrieval strategy.

```python
from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from harnessiq.shared.agents import AgentContextWindow
from harnessiq.shared.tool_selection import (
    ToolProfile,
    ToolSelectionConfig,
    ToolSelectionResult,
)


@runtime_checkable
class DynamicToolSelector(Protocol):
    """Select the active model-visible tool subset for one agent turn."""

    @property
    def config(self) -> ToolSelectionConfig:
        """Return the selector configuration for this agent instance."""

    def index(self, profiles: Sequence[ToolProfile]) -> None:
        """Prepare the selector to rank the provided tool profiles."""

    def select(
        self,
        *,
        context_window: AgentContextWindow,
        candidate_profiles: Sequence[ToolProfile],
    ) -> ToolSelectionResult:
        """Return the selected subset for the next model turn."""
```

If an embedding backend is made injectable, define that seam as a protocol in the same interfaces module:

```python
@runtime_checkable
class EmbeddingBackend(Protocol):
    def embed(self, text: str) -> Sequence[float]:
        """Return a vector representation for retrieval."""
```

This is a better fit for current repository practice than making the selector itself a tool or placing it under `harnessiq/tools/`.

---

## 6. Shared Value Objects

### 6.1 `ToolProfile`

`ToolProfile` is retrieval metadata for a single tool. It should not replace `ToolDefinition`. `ToolDefinition` remains the canonical execution-facing schema. `ToolProfile` is the retrieval-facing metadata used only for narrowing.

Recommended shape:

```python
@dataclass(frozen=True, slots=True)
class ToolProfile:
    key: str
    name: str
    family: str
    description: str
    requires_credentials: bool

    semantic_description: str = ""
    tags: tuple[str, ...] = ()
    when_to_use: str = ""
    limitations: str = ""

    always_on: bool = False
    retrievable: bool = True
```

Important repository note:

- `ToolEntry` in `harnessiq/toolset/catalog_provider.py` must remain the existing lightweight catalog record.
- `ToolProfile` should be a sibling model layered on top of the catalog and runtime tool definitions.
- the dynamic layer should resolve profiles from:
  - existing catalog-backed tools selected by string key
  - additive custom `RegisteredTool` instances passed through the Python API

Recommendation:

- keep `ToolEntry` unchanged
- add `ToolProfile` as a parallel shared model
- add a profile-resolution layer in `harnessiq/toolset/` that derives retrieval metadata from existing catalog entries, tool definitions, and optional authored profile overrides

This keeps the current tool catalog stable while still enabling retrieval-quality metadata.

### 6.2 `ToolSelectionConfig`

This should be an additive runtime configuration object carried by the agent runtime, defaulting to disabled.

```python
@dataclass(frozen=True, slots=True)
class ToolSelectionConfig:
    enabled: bool = False
    top_k: int = 5
    mandatory_tools: tuple[str, ...] = ()
    min_similarity: float = 0.0
    reranker_mode: Literal["none", "auto", "always"] = "none"
    expand_on_miss: bool = True
    debug_logging: bool = False
```

Repository fit:

- place in `harnessiq/shared/tool_selection.py`
- add to `AgentRuntimeConfig` in `harnessiq/shared/agents.py`
- merge it through `merge_agent_runtime_config()`
- leave all built-in agents on the static path by default even after the config is introduced

### 6.3 `ToolSelectionResult`

```python
@dataclass(frozen=True, slots=True)
class ToolSelectionResult:
    selected_keys: tuple[str, ...]
    retrieval_query: str
    scored_tools: tuple[tuple[str, float], ...]
    always_on_keys: tuple[str, ...] = ()
    mandatory_keys: tuple[str, ...] = ()
    rejected_keys: tuple[str, ...] = ()
    fallback_used: bool = False
    reranker_used: bool = False
```

This should be treated as debug and observability data, not as an execution primitive.

---

## 7. Concrete Default Implementation

The default implementation should be a cheap embedding-based selector with optional future reranking.

Recommended implementation class:

```python
class CosineSimilarityDynamicToolSelector:
    ...
```

Recommended home:

- `harnessiq/toolset/dynamic_selector.py`

Why not `harnessiq/tools/`:

- it is not a callable tool surface
- it is a retrieval/catalog concern
- the file index already describes `toolset/` as the static catalog and lookup layer, which is the closest architectural home

Default backend strategy:

- use a provider-backed embedding API as the default embedding backend
- implement that embedding surface in the providers layer
- keep the selector dependent on an embedding interface so alternative backends can still be injected

Hot-path behavior:

1. Build a context signal from the current turn state.
2. Embed that signal.
3. Score against indexed retrievable tool profiles.
4. Apply `top_k`, `min_similarity`, and fallback rules.
5. Union in `always_on` and `mandatory_tools`.
6. Return `ToolSelectionResult`.

This preserves a deterministic, low-latency V1.

---

## 8. Where the Runtime Integrates

### 8.1 `BaseAgent`

The selector has to integrate before model request assembly and before any prompt text renders the active tool set.

That makes `BaseAgent.build_model_request()` the correct integration point.

Refined flow:

1. Collect the current registered tool definitions from the `tool_executor`.
2. Resolve the candidate ceiling:
   - if `allowed_tools` is populated, ceiling is the intersection of registered tool keys and `allowed_tools`
   - if `allowed_tools` is empty, ceiling is all registered tool keys
3. Resolve candidate profiles on top of that ceiling:
   - existing tool keys map onto retrieval profiles via the toolset/profile layer
   - additive custom `RegisteredTool` objects map onto retrieval profiles via runtime profile builders
4. If dynamic selection is disabled, expose the full candidate ceiling to the model.
5. If enabled, run the selector and expose only `selected_keys`.
6. Build prompt/tool rendering from the active tool set, not from the full registered set.
7. Build the final `AgentModelRequest`.

That last requirement matters because some prompt builders render tool text directly.

### 8.2 Prompt-Tool Alignment

Any prompt builder that enumerates tools must render from the active turn-level tool set when dynamic selection is enabled.

High-risk current areas called out by prior repo analysis:

- `harnessiq/agents/provider_base/agent.py`
- `harnessiq/agents/leads/agent.py`

The design must preserve this invariant:

> The tool names described in the prompt and the tool schemas passed to the provider must refer to the same active set for that turn.

If this invariant is not preserved, the model will be told it has tools it cannot actually call.

---

## 9. Turn Lifecycle

When `ToolSelectionConfig.enabled=False`:

1. `BaseAgent.run()` calls `build_model_request()`
2. the agent exposes the normal tool set from the executor
3. the model runs as it does today
4. execution is still gated by the hook-based allowlist

When `ToolSelectionConfig.enabled=True`:

1. `BaseAgent.run()` calls `build_model_request()`
2. `BaseAgent` builds the candidate ceiling from registered tools plus `allowed_tools`
3. `BaseAgent` asks the selector for an active subset
4. prompt rendering and tool schema exposure both use the active subset
5. the model runs with the narrowed set
6. execution still flows through the same hook-based policy gate

This means the dynamic layer changes only model visibility, not execution authority.

---

## 10. `always_on` and Required Runtime Tools

Some tools should not be subject to retrieval narrowing.

Examples:

- compaction tools
- control tools that are part of the agent safety model
- context tools required for reset or durable-memory handling
- other agent-critical bookkeeping tools whose absence could strand the runtime

These should be represented through `always_on=True` at the `ToolProfile` layer.

`mandatory_tools` in `ToolSelectionConfig` handles the per-agent version of the same rule.

Repository-specific guidance:

- be conservative for V1
- if a tool participates in reset, compaction, control, or durable-memory invariants, default it to always-on
- only make a tool retrievable-only if its absence on a turn is operationally safe

---

## 11. Retrieval Metadata Guidance

The earlier design correctly identified that retrieval quality depends more on metadata quality than on the scoring algorithm.

Recommended fields and intent:

- `description`
  - short listing text
- `semantic_description`
  - richer capability description
- `tags`
  - short functional keywords
- `when_to_use`
  - situation-framed trigger description
- `limitations`
  - explicit non-use cases and boundaries

The most important field is `when_to_use`.

Correct pattern:

```text
Use when the agent has already verified an output and needs to persist it
before a context reset or before moving to the next stage. Not for drafts
or intermediate work.
```

Incorrect pattern:

```text
Writes a verified output to durable storage.
```

That second example only restates capability. The selector needs situation framing.

---

## 12. Interface and Config Placement

To better match repository practice, the previous "new file" mapping should be refined as follows.

### 12.1 New Files

Recommended:

- `harnessiq/interfaces/tool_selection.py`
  - `DynamicToolSelector`
  - `EmbeddingBackend`
- `harnessiq/shared/tool_selection.py`
  - `ToolProfile`
  - `ToolSelectionConfig`
  - `ToolSelectionResult`
- `harnessiq/toolset/dynamic_selector.py`
  - default concrete selector implementation
- provider embedding client modules under `harnessiq/providers/`
  - default provider-backed embedding transport for the selector
- `docs/dynamic-tool-selection.md`
  - harness-author-facing guide

### 12.2 Files Likely Modified

- `harnessiq/interfaces/__init__.py`
  - export new selector interfaces
- `harnessiq/shared/agents.py`
  - add `tool_selection` config to runtime config
- `harnessiq/agents/base/agent.py`
  - compute active tool keys before request construction
- `harnessiq/toolset/catalog_provider.py`
  - if any helper needs catalog access, keep changes additive and do not redefine `ToolEntry`
- `harnessiq/agents/provider_base/agent.py`
  - render active tool list, not unconditional full list
- `harnessiq/agents/leads/agent.py`
  - render active tool list, not unconditional full list
- CLI modules that expose runtime configuration
  - add opt-in flags only

---

## 13. Configuration Semantics

Recommended merge behavior for `ToolSelectionConfig` inside `merge_agent_runtime_config()`:

- `enabled`
  - child override if explicitly provided, otherwise preserve parent
- `top_k`
  - child wins
- `mandatory_tools`
  - union
- `min_similarity`
  - child wins
- `reranker_mode`
  - child wins
- `expand_on_miss`
  - child wins
- `debug_logging`
  - child wins

This is simpler and safer than special-case OR semantics for every field.

---

## 14. Packaging and Dependency Guidance

The concrete selector should not hard-code one embedding dependency into the runtime contract.

Recommended design:

- the interface depends on an `EmbeddingBackend` protocol
- the default implementation uses a provider-backed embedding client implemented in the providers layer
- the runtime can also accept an externally provided embedding backend

This keeps the design compatible with:

- provider-hosted embeddings as the default path
- future cached or remote vector services
- alternative injected backends for advanced users

The runtime contract stays stable even if the default backend changes.

---

## 15. Phased Plan

### V1

Scope:

- interface-first selector seam
- shared config/value objects
- default cosine-similarity selector
- provider-backed embedding backend
- additive retrieval-profile layer built on top of the existing catalog
- opt-in runtime integration
- prompt/tool alignment fixes
- no reranker
- no metadata auto-generation

Deliverables:

- `DynamicToolSelector` protocol
- `ToolSelectionConfig` on runtime config
- active-tool-set request construction in `BaseAgent`
- retrieval-profile resolution for catalog-backed keys plus additive custom tools
- authored retrieval metadata or reasonable default profile building for the surfaces exposed through dynamic enablement
- tests covering:
  - disabled path unchanged
  - subset invariant
  - always-on preservation
  - candidate ceiling enforcement
  - prompt/tool alignment

### V2

Scope:

- optional reranking
- debug logging / ledger surfacing of `ToolSelectionResult`
- metadata generation helpers for incomplete profiles

### V3

Scope:

- recovery strategy when the narrowed tool set was too small
- adaptive expansion or retry behavior

---

## 16. Open Decisions

### Q1. Should `ToolProfile` extend `ToolEntry` or remain separate?

Recommendation:

- keep them separate
- `ToolEntry` remains unchanged as lightweight catalog metadata
- `ToolProfile` becomes the retrieval-focused overlay built on top of the current catalog and runtime tool definitions

### Q2. Where should the default implementation live?

Recommendation:

- interface in `harnessiq/interfaces/tool_selection.py`
- implementation in `harnessiq/toolset/dynamic_selector.py`
- default embedding transport in the providers layer

This is the best fit for the current package structure.

### Q3. Should dynamic selection be allowed when `allowed_tools` is empty?

Recommendation:

- yes
- interpret empty `allowed_tools` as "no explicit ceiling configured"
- candidate pool becomes the full registered tool set

This matches current runtime behavior better than treating empty `allowed_tools` as "no tools."

### Q4. How should initial metadata be authored?

Recommendation:

- build reasonable retrieval profiles on top of the existing catalog and tool definitions
- allow authored overrides where retrieval quality needs improvement
- keep all built-in agents disabled by default until future opt-in decisions are made

---

## 17. What Does Not Change

- Static tool registration remains the default.
- The hook-based approval and allowlist gate remains authoritative.
- Existing agents do not incur embedding or selection latency unless they opt in.
- Tool execution still flows through `tool_executor.execute(...)`.
- Durable memory and reset semantics remain unchanged.
- Existing harnesses do not need to adopt the feature.

---

## 18. Final Position

This feature should be framed as:

- static tool registration by default
- dynamic tool visibility as an optional agent-level runtime strategy
- interface-first in `harnessiq/interfaces/`
- shared value objects in `harnessiq/shared/`
- default implementation behind that interface in `harnessiq/toolset/`

That shape matches the repository's current boundaries much better than introducing the selector as a new executable tool family or treating `allowed_tools` as if it already controlled model-visible schemas.

If implemented this way, dynamic tool selection becomes a clean additive layer on top of the current runtime rather than a rewrite of the tool system.
