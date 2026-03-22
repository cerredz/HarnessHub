## Stage 1 - Static Analysis

No repository-configured linter is present for this slice. I inspected `pyproject.toml` and found no `ruff`, `flake8`, or equivalent configuration. Applied manual style verification to:
- `harnessiq/shared/http.py`
- `tests/test_provider_base.py`
- `tests/test_providers.py`

Result: pass.

## Stage 2 - Type Checking

No repository-configured type checker is present for this slice. I inspected `pyproject.toml` and found no `mypy`, `pyright`, or equivalent configuration. The change preserves explicit parameter and return annotations on the modified code paths.

Result: pass.

## Stage 3 - Unit Tests

Command:
```powershell
python -m unittest tests.test_provider_base tests.test_providers tests.test_grok_provider
```

Observed result:
- `Ran 26 tests`
- `OK`

Result: pass.

## Stage 4 - Integration & Contract Tests

There is no separately configured integration or contract test suite for this ticketed slice. The closest contract boundary is the shared provider/tracing behavior covered by the targeted unittest suites above, which exercise:
- HTTP transport error wrapping
- LangSmith tracing wrappers
- Grok provider client request plumbing

No additional integration harness is configured in the repository for this path.

Result: pass for available coverage.

## Stage 5 - Smoke & Manual Verification

### Direct traceback reproduction

Command:
```powershell
@'
from harnessiq.shared.http import ProviderHTTPError
try:
    raise ProviderHTTPError(provider='grok', message='Forbidden', status_code=403, url='https://api.x.ai/v1/chat/completions')
except ProviderHTTPError as exc:
    exc.__traceback__ = exc.__traceback__
    print({'type': type(exc).__name__, 'text': str(exc), 'status_code': exc.status_code, 'url': exc.url})
'@ | python -
```

Observed output:
```text
{'type': 'ProviderHTTPError', 'text': 'grok request failed (403): Forbidden', 'status_code': 403, 'url': 'https://api.x.ai/v1/chat/completions'}
```

Confirmation:
- traceback assignment succeeds
- no secondary `TypeError` is raised

### Instagram/Grok CLI smoke

Command:
```powershell
$env:XAI_API_KEY=<repo .env value>
python -m harnessiq.cli instagram prepare --agent traceback-fix-smoke
python -m harnessiq.cli instagram configure --agent traceback-fix-smoke --icp "influencers in the ai educational / educational niche" --runtime-param search_result_limit=1
python -m harnessiq.cli instagram run --agent traceback-fix-smoke --model-factory harnessiq.integrations.grok_model:create_grok_model --max-cycles 1
```

Observed result:
- the run still fails upstream with `403 Forbidden`
- the surfaced application error is now:
  `harnessiq.shared.http.ProviderHTTPError: grok request failed (403): Forbidden`
- the previous masking error `TypeError("super(type, obj): obj must be an instance or subtype of type")` does not appear

Confirmation:
- the user-reported traceback regression is fixed
- upstream Grok auth/authorization behavior is unchanged, which is expected and in scope
