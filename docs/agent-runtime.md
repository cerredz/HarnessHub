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

## Credential Bindings

Harnessiq can also persist repo-local credential bindings that resolve against a `.env` file:

```python
from harnessiq.config import AgentCredentialBinding, CredentialEnvReference, CredentialsConfigStore

store = CredentialsConfigStore(".")
store.upsert(
    AgentCredentialBinding(
        agent_name="email_agent",
        references=(CredentialEnvReference(field_name="api_key", env_var="RESEND_API_KEY"),),
    )
)

resolved = store.resolve_agent("email_agent")
print(resolved.as_redacted_dict())
```
