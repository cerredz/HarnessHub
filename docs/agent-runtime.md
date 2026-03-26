# Agent Runtime Example

Harnessiq agents are provider-agnostic. You supply a model adapter that implements the `AgentModel` protocol.

```python
from harnessiq.agents import (
    AgentModelRequest,
    AgentModelResponse,
    BaseAgent,
    json_parameter_section,
)
from harnessiq.tools import create_builtin_registry


class StaticModel:
    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        return AgentModelResponse(
            assistant_message="Done.",
            should_continue=False,
        )


class DemoAgent(BaseAgent):
    def build_system_prompt(self) -> str:
        return "You are a precise demo agent."

    def load_parameter_sections(self):
        return [json_parameter_section("Goal", {"task": "Demonstrate the Harnessiq runtime."})]


agent = DemoAgent(
    name="demo_agent",
    model=StaticModel(),
    tool_executor=create_builtin_registry(),
)

result = agent.run(max_cycles=1)
print(result.status)
```

Harnessiq now ships provider-backed adapters under `harnessiq.integrations`, so most SDK consumers no longer need to write their own `AgentModel` wrapper just to get started.

```python
from harnessiq.integrations import create_model_from_spec

model = create_model_from_spec("openai:gpt-5.4")

agent = DemoAgent(
    name="demo_agent",
    model=model,
    tool_executor=create_builtin_registry(),
)
```

Supported first-class providers are `openai`, `anthropic`, `gemini`, and `grok`. The adapters read credentials from the corresponding environment variables, for example `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` / `GOOGLE_API_KEY`, or `XAI_API_KEY`.

If you want reusable named settings such as `reasoning_effort`, `temperature`, or `max_output_tokens`, persist a profile once and reuse it from the CLI:

```bash
harnessiq models add --name work --model grok:grok-4-1-fast-reasoning --reasoning-effort high
harnessiq models list
```

`BaseAgent` runtime behavior is configured with `AgentRuntimeConfig`:

```python
from harnessiq.agents import AgentRuntimeConfig

runtime = AgentRuntimeConfig(
    max_tokens=80_000,
    reset_threshold=0.9,
    prune_progress_interval=25,
    prune_token_limit=60_000,
)
```

- `max_tokens`: total context budget used for reset heuristics.
- `reset_threshold`: fraction of `max_tokens` that triggers a transcript reset.
- `prune_progress_interval`: deterministic pruning cadence based on a durable progress counter exposed by the agent.
- `prune_token_limit`: optional hard cap that triggers pruning even if the progress interval has not elapsed.

Concrete agents can override `pruning_progress_value()` to tie pruning to durable work instead of raw transcript size. The leads agent uses this to prune after a configurable number of persisted searches while preserving the durable search summaries in parameter sections.

For custom agents, `json_parameter_section()` is the SDK helper for durable JSON-backed memory blocks, and `build_context_window()` / `inspect_tools()` expose the assembled runtime state for debugging and orchestration.

Harnessiq also exposes declarative harness manifests for the built-in agents. These manifests live under `harnessiq.shared` and capture stable metadata such as prompt paths, runtime/custom parameter specs, durable memory files, provider families, and structured output contracts.

```python
from harnessiq.agents import get_harness_manifest

manifest = get_harness_manifest("linkedin")
print(manifest.prompt_path)
print(manifest.runtime_parameter_names)
```

CLI command modules now use the same manifest-backed parameter specs for runtime validation, so custom harness integrations can import one shared source of truth instead of duplicating supported-key lists and coercion rules.
