# Agent Runtime Example

Harnessiq agents are provider-agnostic. You supply a model adapter that implements the `AgentModel` protocol.

```python
from harnessiq.agents import (
    AgentModelRequest,
    AgentModelResponse,
    AgentParameterSection,
    BaseAgent,
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

    def load_parameter_sections(self) -> list[AgentParameterSection]:
        return [AgentParameterSection(title="Goal", content="Demonstrate the Harnessiq runtime.")]


agent = DemoAgent(
    name="demo_agent",
    model=StaticModel(),
    tool_executor=create_builtin_registry(),
)

result = agent.run(max_cycles=1)
print(result.status)
```

For production usage, replace `StaticModel` with your own adapter around the provider/client layer you want to use.
