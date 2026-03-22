# Ticket 5: PhantomBuster Provider

## Title
Add `harnessiq/providers/phantombuster/` — full PhantomBuster API client

## Intent
Implement a complete PhantomBuster provider package. PhantomBuster is a web automation platform (phantoms = automation scripts). The API covers agent (automation) management, launching/aborting executions, retrieving output, organization management, and script discovery.

## Scope
**Creates:**
- `harnessiq/providers/phantombuster/__init__.py`
- `harnessiq/providers/phantombuster/api.py`
- `harnessiq/providers/phantombuster/client.py`
- `harnessiq/providers/phantombuster/requests.py`
- `harnessiq/providers/phantombuster/credentials.py`
- `tests/test_phantombuster_provider.py`

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/phantombuster/__init__.py` | Create: public exports |
| `harnessiq/providers/phantombuster/api.py` | Create: URL, headers |
| `harnessiq/providers/phantombuster/client.py` | Create: `PhantomBusterClient` dataclass |
| `harnessiq/providers/phantombuster/requests.py` | Create: request builders |
| `harnessiq/providers/phantombuster/credentials.py` | Create: `PhantomBusterCredentials` TypedDict |
| `tests/test_phantombuster_provider.py` | Create: unit tests |

## API Reference

**Base URL:** `https://api.phantombuster.com`
**Authentication:** `X-Phantombuster-Key: {api_key}` header

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| GET | /api/v2/agents/fetch | Get agent by ID (`id` query param) |
| GET | /api/v2/agents/fetch-all | List all agents |
| POST | /api/v2/agents/launch | Launch an agent (`id`, `output`, `arguments`, `manualLaunch`) |
| POST | /api/v2/agents/abort | Abort a running agent (`id`) |
| DELETE | /api/v2/agents/delete | Delete an agent (`id`) |
| GET | /api/v2/agents/fetch-output | Fetch agent output (`id`, optional `withOutput`, `mode`) |
| POST | /api/v2/agents/save-agent-argument | Save/update agent argument (`id`, `argument`) |
| GET | /api/v2/containers/fetch | Get container/execution details (`id`) |
| GET | /api/v2/containers/fetch-all | List containers for an agent (`agentId`, optional `status`) |
| POST | /api/v2/phantoms/fetch | Get phantom (template) details (`id`) |
| GET | /api/v2/phantoms/fetch-all | List available phantom templates |
| GET | /api/v2/user/me | Get current user info |
| GET | /api/v2/orgs/fetch-members | List organization members |
| GET | /api/v2/scripts/fetch-all | List automation scripts |
| GET | /api/v2/scripts/fetch | Get script details (`id`) |

## Approach

**`credentials.py`:**
```python
class PhantomBusterCredentials(ProviderCredentialConfig):
    api_key: str
```

**`api.py`:**
- `DEFAULT_BASE_URL = "https://api.phantombuster.com"`
- `build_headers(api_key)` → `{"X-Phantombuster-Key": api_key}`
- URL builders: `agents_fetch_url()`, `agents_fetch_all_url()`, `agents_launch_url()`, `agents_abort_url()`, `agents_delete_url()`, `agents_fetch_output_url()`, `agents_save_argument_url()`, `containers_fetch_url()`, `containers_fetch_all_url()`, `phantoms_fetch_url()`, `phantoms_fetch_all_url()`, `user_me_url()`, `orgs_fetch_members_url()`, `scripts_fetch_all_url()`, `scripts_fetch_url()`

**`requests.py`:**
- `build_launch_agent_request(agent_id, *, output, arguments, manual_launch)` — POST body
- `build_abort_agent_request(agent_id)` — POST body `{"id": agent_id}`
- `build_delete_agent_request(agent_id)` — POST body `{"id": agent_id}`
- `build_fetch_agent_params(agent_id)` — query params dict `{"id": agent_id}`
- `build_fetch_output_params(agent_id, *, with_output, mode)` — query params
- `build_fetch_containers_params(agent_id, *, status)` — query params
- `build_save_argument_request(agent_id, argument)` — POST body
- `build_fetch_phantom_request(phantom_id)` — POST body `{"id": phantom_id}`

**`client.py`:**
```python
@dataclass(frozen=True, slots=True)
class PhantomBusterClient:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json
```
Methods: `fetch_agent(agent_id)`, `fetch_all_agents()`, `launch_agent(agent_id, ...)`, `abort_agent(agent_id)`, `delete_agent(agent_id)`, `fetch_agent_output(agent_id, ...)`, `save_agent_argument(agent_id, argument)`, `fetch_container(container_id)`, `fetch_containers(agent_id, ...)`, `fetch_phantom(phantom_id)`, `fetch_all_phantoms()`, `get_user_info()`, `get_org_members()`, `fetch_all_scripts()`, `fetch_script(script_id)`

## Assumptions
- `fetch_agent`, `fetch_output`, `fetch_containers` are GET with query params.
- `launch`, `abort`, `delete`, `save_argument` are POST/DELETE with JSON body.
- `phantoms/fetch` is a POST (as documented).
- `output` in launch request refers to "last" or "result-object".

## Acceptance Criteria
- [ ] `from harnessiq.providers.phantombuster import PhantomBusterClient, PhantomBusterCredentials` works
- [ ] `build_launch_agent_request("ag_1", output="result-object")` returns `{"id": "ag_1", "output": "result-object"}`
- [ ] `build_fetch_agent_params("ag_1")` returns `{"id": "ag_1"}`
- [ ] `build_headers(api_key)` uses `X-Phantombuster-Key` header name
- [ ] Optional fields omitted when `None`
- [ ] All existing tests remain green

## Verification Steps
1. `python -m pytest tests/test_phantombuster_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -c "from harnessiq.providers.phantombuster import PhantomBusterClient; print('ok')"`
4. `python -m py_compile harnessiq/providers/phantombuster/*.py`

## Dependencies
- Ticket 1

## Drift Guard
Must not touch agent modules, other providers, or existing test files.
