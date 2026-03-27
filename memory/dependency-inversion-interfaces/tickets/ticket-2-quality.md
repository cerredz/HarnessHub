## Stage 1 - Static Analysis

No dedicated linter or static-analysis command is configured in `pyproject.toml` or `requirements.txt`.

Manual validation applied instead:

- Reviewed the contract-import changes across the repeated `prepare_request` families.
- Verified the refactor only touched operation-factory typing/import seams and did not alter request-building logic.
- Confirmed direct-method families such as Browser Use and Google Drive were intentionally left untouched.

## Stage 2 - Type Checking

No dedicated type-checking command is configured in `pyproject.toml`.

Manual typing validation applied instead:

- Operation-factory `client=` parameters now type against `RequestPreparingClient` where the concrete client surface is not required.
- Local `_coerce_client(...)` helpers now return `RequestPreparingClient` while preserving concrete credential-to-client construction paths.
- Added a regression test proving a protocol-compatible fake client works for `create_exa_tools(...)`.

## Stage 3 - Unit Tests

Commands:

```powershell
pytest tests/test_exa_provider.py tests/test_apollo_provider.py tests/test_serper_provider.py tests/test_tools.py
pytest tests/test_browser_use_provider.py tests/test_creatify_provider.py tests/test_instantly_provider.py tests/test_smartlead_provider.py tests/test_zerobounce_provider.py
pytest tests/test_arcads_provider.py tests/test_attio_provider.py tests/test_expandi_provider.py tests/test_inboxapp_provider.py tests/test_lemlist_provider.py tests/test_lusha_provider.py tests/test_outreach_provider.py tests/test_paperclip_provider.py
```

Result: passed

- 81 tests passed in the first provider/tool slice.
- 120 tests passed in the second provider slice.
- 220 tests passed in the third provider slice.

## Stage 4 - Integration & Contract Tests

Commands:

```powershell
pytest tests/test_browser_use_provider.py tests/test_creatify_provider.py tests/test_instantly_provider.py tests/test_smartlead_provider.py tests/test_zerobounce_provider.py
pytest tests/test_arcads_provider.py tests/test_attio_provider.py tests/test_expandi_provider.py tests/test_inboxapp_provider.py tests/test_lemlist_provider.py tests/test_lusha_provider.py tests/test_outreach_provider.py tests/test_paperclip_provider.py
```

Result: passed

- 120 tests passed in the broader provider contract slice.
- 220 tests passed in the remaining patched provider families.

Additional audit note:

- I also ran `pytest tests/test_sdk_package.py` once during validation.
- It failed in `HarnessiqPackageTests.test_agents_and_providers_keep_shared_definitions_out_of_local_modules` because of pre-existing `harnessiq/providers/gcloud/client.py` violations unrelated to this ticket.
- That audit was intentionally not treated as the Stage 4 gate because fixing it would expand into an unrelated package-structure task outside this ticket’s drift guard.

## Stage 5 - Smoke & Manual Verification

Command:

```powershell
@'
from harnessiq.shared.tools import EXA_REQUEST
from harnessiq.tools.exa import create_exa_tools
from harnessiq.tools.registry import ToolRegistry

class FakeCredentials:
    timeout_seconds = 21.0

class FakePreparedRequest:
    def __init__(self, operation_name: str) -> None:
        self.operation = type('Operation', (), {'name': operation_name})()
        self.method = 'POST'
        self.path = '/search'
        self.url = 'https://example.test/search'
        self.headers = {'Authorization': 'Bearer fake'}
        self.json_body = {'query': 'AI'}

class FakeClient:
    def __init__(self) -> None:
        self.credentials = FakeCredentials()
    def prepare_request(self, operation_name: str, *, path_params=None, query=None, payload=None):
        return FakePreparedRequest(operation_name)
    def request_executor(self, method: str, url: str, **kwargs):
        return {'method': method, 'url': url, 'timeout_seconds': kwargs['timeout_seconds']}

registry = ToolRegistry(create_exa_tools(client=FakeClient()))
result = registry.execute(EXA_REQUEST, {'operation': 'search', 'payload': {'query': 'AI'}})
print(result.output['operation'])
print(result.output['response']['timeout_seconds'])
'@ | python -
```

Observed output:

```text
search
21.0
```

Confirmation:

- `create_exa_tools(...)` accepts a protocol-compatible fake client rather than requiring the concrete `ExaClient` type.
- The runtime still routes timeout values through the expected request-executor path.
