## Stage 1 - Static Analysis

No dedicated linter or static-analysis command is configured in `pyproject.toml` or `requirements.txt`.

Manual validation applied instead:

- Reviewed the constructor and property type changes to confirm the refactor stays limited to agent dependency seams.
- Verified the only non-agent runtime additions are the Resend-specific client contract and its minimal type adoption in the Resend tool factory/helpers.
- Confirmed no prompt, ledger, CLI, or output-sink behavior changed in this ticket.

## Stage 2 - Type Checking

No dedicated type-checking command is configured in `pyproject.toml`.

Manual typing validation applied instead:

- Apollo, Exa, Instantly, and Outreach reusable agent harnesses now accept `RequestPreparingClient` dependencies.
- The email harness now accepts `ResendRequestClient`, which preserves the richer Resend `prepare_request(...)` keyword surface.
- Concrete default client construction is unchanged in every agent constructor.

## Stage 3 - Unit Tests

Commands:

```powershell
pytest tests/test_interfaces.py tests/test_provider_base_agents.py
pytest tests/test_apollo_agent.py tests/test_exa_agent.py tests/test_email_agent.py tests/test_instantly_agent.py tests/test_outreach_agent.py
```

Result: passed

- 18 tests passed in the shared interface/provider-base slice.
- 23 tests passed in the agent-focused slice.

## Stage 4 - Integration & Contract Tests

Command:

```powershell
pytest tests/test_resend_tools.py
```

Result: passed

- 7 tests passed.
- This confirms the minimal Resend tool-factory typing change remains compatible with the existing Resend tooling behavior used by `BaseEmailAgent`.

## Stage 5 - Smoke & Manual Verification

Command:

```powershell
@'
from tempfile import TemporaryDirectory

from harnessiq.agents import AgentModelResponse, AgentParameterSection
from harnessiq.agents.apollo import ApolloAgentConfig, BaseApolloAgent
from harnessiq.providers.apollo import ApolloCredentials
from harnessiq.shared.tools import APOLLO_REQUEST, ToolCall

class FakeModel:
    def __init__(self):
        self.requests = []
    def generate_turn(self, request):
        self.requests.append(request)
        return AgentModelResponse(
            assistant_message='Search Apollo people.',
            tool_calls=(ToolCall(tool_key=APOLLO_REQUEST, arguments={'operation': 'search_people', 'payload': {'person_titles': ['VP Sales']}}),),
            should_continue=False,
        )

class FakeApolloClient:
    def __init__(self, credentials):
        self.credentials = credentials
    def request_executor(self, method, url, **kwargs):
        return {'method': method, 'url': url, 'timeout_seconds': kwargs['timeout_seconds']}
    def prepare_request(self, operation_name, *, path_params=None, query=None, payload=None):
        return type('PreparedRequest', (), {
            'operation': type('Operation', (), {'name': operation_name})(),
            'method': 'POST',
            'path': '/mixed_people/api_search',
            'url': 'https://api.apollo.io/api/v1/mixed_people/api_search',
            'headers': {'X-Api-Key': 'apollo-secret-key'},
            'json_body': payload,
        })()

class DemoApolloAgent(BaseApolloAgent):
    def apollo_objective(self):
        return 'Find Apollo prospects.'
    def load_apollo_parameter_sections(self):
        return [AgentParameterSection(title='Apollo Brief', content='Target VP Sales personas.')]

with TemporaryDirectory() as temp_repo_root:
    credentials = ApolloCredentials(api_key='apollo-secret-key')
    agent = DemoApolloAgent(
        name='demo_apollo_agent',
        model=FakeModel(),
        config=ApolloAgentConfig(apollo_credentials=credentials),
        apollo_client=FakeApolloClient(credentials),
        repo_root=temp_repo_root,
    )
    result = agent.run(max_cycles=1)
    print(result.status)
    print(agent.transcript[-1].tool_key)
'@ | python -
```

Observed output:

```text
completed
apollo.request
```

Confirmation:

- A protocol-compatible fake Apollo client can drive a real provider-backed agent harness end to end.
- The agent still uses the expected Apollo tool key and completes normally.
