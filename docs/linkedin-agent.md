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

## CLI Workflow

Harnessiq now ships a scriptable LinkedIn CLI under `harnessiq linkedin`.

Prepare or update a per-agent memory folder:

```bash
harnessiq linkedin configure \
  --agent candidate-a \
  --memory-root ./memory/linkedin \
  --job-preferences-text "Senior platform engineering roles" \
  --user-profile-file ./profile.md \
  --runtime-param max_tokens=4000 \
  --runtime-param notify_on_pause=false \
  --custom-param target_team=platform \
  --additional-prompt-text "Prefer remote-first companies" \
  --import-file ./resume.pdf \
  --inline-file cover-letter.txt="Short cover letter text"
```

Inspect the current managed state:

```bash
harnessiq linkedin show --agent candidate-a --memory-root ./memory/linkedin
```

Run the agent from persisted state:

```bash
harnessiq linkedin run \
  --agent candidate-a \
  --memory-root ./memory/linkedin \
  --model-factory myproject.factories:create_linkedin_model \
  --browser-tools-factory myproject.factories:create_linkedin_browser_tools \
  --max-cycles 5
```

Runtime notes:

- Each `--agent` value maps to its own managed memory folder under `--memory-root`.
- Imported files are copied into managed storage and recorded with their original source paths.
- The CLI persists agent-aligned runtime params, arbitrary custom key/value data, and free-form prompt text.
- The SDK does not currently ship a provider-backed `AgentModel` adapter, so `run` expects an importable factory that returns a compatible model object.
