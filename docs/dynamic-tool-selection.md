# Dynamic Tool Selection

Harnessiq agents remain static by default. If you do nothing, a concrete agent exposes the same tool surface it does today.

Dynamic tool selection is an opt-in runtime layer that narrows the model-visible tool set per turn without changing the underlying execution surface:

- registered tools: what the runtime can execute
- `allowed_tools`: the execution ceiling enforced by the existing approval/allowlist hook
- dynamic selection: a per-turn subset of the current tool surface shown to the model

This keeps the current tool catalog intact. The selector is built on top of the live tool definitions and existing tool families instead of rewriting the catalog itself.

## When To Use It

Use dynamic tool selection when an agent carries a wide tool surface and only a small portion is relevant on any given turn. Typical candidates:

- provider-heavy harnesses that expose many provider request tools
- agents with multiple tool families that activate in different phases
- harnesses where tool-schema tokens crowd out useful transcript context

Do not enable it just because it exists. If an agent has a small, stable tool surface, the static path is simpler and remains the preferred default.

## Runtime Model

When `tool_selection.enabled=False`, `BaseAgent` keeps the existing behavior and exposes the full runtime tool surface for the turn.

When `tool_selection.enabled=True`, the runtime:

1. collects the currently available tool definitions
2. applies the optional `allowed_tools` ceiling
3. applies the optional dynamic candidate patterns
4. resolves retrieval profiles from the live tool definitions
5. asks the configured selector for the active turn-level subset
6. renders prompt text and tool schemas from that active subset

The selector never grants new authority. A selected tool must already be part of the current runtime surface, and if `allowed_tools` is configured it must also match that ceiling.

## Python Configuration

```python
from harnessiq.agents import AgentRuntimeConfig
from harnessiq.shared.tool_selection import ToolSelectionConfig

runtime_config = AgentRuntimeConfig(
    allowed_tools=("apollo.*", "filesystem.*"),
    tool_selection=ToolSelectionConfig(
        enabled=True,
        top_k=4,
        candidate_tool_keys=("apollo.request", "filesystem.*"),
        embedding_model="openai:text-embedding-3-small",
    ),
)
```

Key fields:

- `enabled`: keeps the feature off unless explicitly enabled
- `top_k`: number of retrieved tools exposed per turn
- `candidate_tool_keys`: optional pattern filter inside the live runtime tool surface
- `embedding_model`: provider-backed embedding model spec in `provider:model` form

## CLI Configuration

The run commands for the built-in harnesses now accept dynamic-selection flags:

```bash
harnessiq leads run \
  --agent campaign-a \
  --model openai:gpt-5.4 \
  --dynamic-tools \
  --dynamic-tool-candidates "apollo.request,filesystem.*" \
  --dynamic-tool-top-k 3 \
  --dynamic-tool-embedding-model openai:text-embedding-3-small
```

CLI support is intentionally limited to existing tool keys and family patterns. Custom callables are still a Python construction concern because the CLI cannot serialize arbitrary Python functions into a safe runtime contract.

## Custom Tools

Dynamic selection works with additive custom tools as long as those tools are already part of the agent's runtime tool surface.

```python
from harnessiq.agents import LeadsAgent
from harnessiq.toolset import define_tool

custom_tool = define_tool(
    key="custom.resume_summary",
    description="Summarize a profile before saving a lead.",
    parameters={},
    handler=lambda arguments: {"summary": "concise profile"},
)

agent = LeadsAgent(
    model=model,
    company_background="We sell outbound infrastructure.",
    icps=("VP Sales",),
    platforms=("apollo",),
    tools=(custom_tool,),
    runtime_config=runtime_config,
)
```

The selector resolves retrieval metadata from the live tool definitions, so custom tools participate without requiring catalog rewrites.

## Embeddings

The default path uses a provider-backed embedding backend through the providers layer. The default spec is:

- `openai:text-embedding-3-small`

You can override it per agent or per CLI run with `ToolSelectionConfig.embedding_model` or `--dynamic-tool-embedding-model`.

## What Does Not Change

- Built-in agents are still on the static path by default.
- The existing approval and `allowed_tools` policy hook still controls execution authority.
- The tool catalog remains the source of executable tool definitions.
- Dynamic selection does not add reranking or recovery behavior in V1.

For the surrounding runtime and tool-composition APIs, see [docs/agent-runtime.md](./agent-runtime.md) and [docs/tools.md](./tools.md).
