# LinkedIn Agent Example

`LinkedInJobApplierAgent` is a first-class SDK export for LinkedIn job application workflows with durable memory.

```python
from harnessiq.agents import AgentModelRequest, AgentModelResponse, LinkedInJobApplierAgent


class StaticModel:
    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        return AgentModelResponse(
            assistant_message="Review complete.",
            should_continue=False,
        )


agent = LinkedInJobApplierAgent(
    model=StaticModel(),
    memory_path="./memory/linkedin",
)

result = agent.run(max_cycles=1)
print(result.status)
```

Notes:

- The agent bootstraps its memory files automatically under `memory_path`.
- The default browser tools are stubs that raise until you inject real runtime handlers through `browser_tools`.
- Durable state such as job preferences, user profile, action logs, and applied jobs are preserved on disk.
