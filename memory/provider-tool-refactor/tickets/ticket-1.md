# Ticket 1 — Move provider credential TypedDicts to `harnessiq/shared/`

## Title
Move all data provider credential TypedDicts from `providers/{name}/credentials.py` to `harnessiq/shared/`

## Intent
The file index states that "definitions that need to be reused across modules should live in `harnessiq/shared/` in domain-specific files." Eight data providers each have standalone `credentials.py` files containing TypedDict subclasses of `ProviderCredentialConfig`. Centralising these in `shared/` means agents and tools can import credential types from a single authoritative location rather than reaching into individual provider directories.

## Scope
**In scope:**
- Create `harnessiq/shared/credentials.py` with all 8 provider credential TypedDicts
- Thin down each `providers/{name}/credentials.py` to a backward-compat re-export from `shared/`
- Update each provider `client.py` and `__init__.py` to import credentials from `shared/`
- Update all test files that reference the old credential imports

**Out of scope:**
- LLM provider credentials (anthropic, openai, grok, gemini) — they don't use the ProviderCredentialConfig pattern
- Config/loader layer (`harnessiq/config/`) — out of scope
- Adding new credential fields

## Relevant Files
- `harnessiq/shared/credentials.py` — **create**: all 8 TypedDicts
- `harnessiq/providers/coresignal/credentials.py` — **update**: re-export from shared
- `harnessiq/providers/leadiq/credentials.py` — **update**: re-export from shared
- `harnessiq/providers/peopledatalabs/credentials.py` — **update**: re-export from shared
- `harnessiq/providers/phantombuster/credentials.py` — **update**: re-export from shared
- `harnessiq/providers/proxycurl/credentials.py` — **update**: re-export from shared
- `harnessiq/providers/salesforge/credentials.py` — **update**: re-export from shared
- `harnessiq/providers/snovio/credentials.py` — **update**: re-export from shared
- `harnessiq/providers/zoominfo/credentials.py` — **update**: re-export from shared
- `harnessiq/shared/__init__.py` — **update**: export credential types
- Tests for each provider — **update**: any direct credential import paths

## Approach
1. Read each provider `credentials.py` to collect all TypedDicts.
2. Create `harnessiq/shared/credentials.py` with imports from `harnessiq/config/models.py` and all 8 TypedDicts.
3. Replace each `providers/{name}/credentials.py` with a one-line re-export: `from harnessiq.shared.credentials import XCredentials as XCredentials`.
4. Audit `client.py` and `__init__.py` in each provider for credential imports; update to point at `shared.credentials`.
5. Run tests to confirm no import errors.

## Assumptions
- `ProviderCredentialConfig` base type stays in `harnessiq/config/models.py`; only the concrete TypedDicts move.
- The backward-compat re-exports in provider credential files preserve existing import paths so other in-flight work is not broken.

## Acceptance Criteria
- [ ] `harnessiq/shared/credentials.py` exists and contains all 8 provider TypedDicts
- [ ] Each TypedDict is importable directly from `harnessiq.shared.credentials`
- [ ] Each `providers/{name}/credentials.py` re-exports its TypedDict from shared
- [ ] All existing tests pass without modification to test files
- [ ] `mypy` reports no new type errors

## Verification Steps
1. `python -c "from harnessiq.shared.credentials import SnovioCredentials, ZoomInfoCredentials, LeadIQCredentials, SalesforgeCredentials, PhantomBusterCredentials, PeopleDataLabsCredentials, ProxycurlCredentials, CoresignalCredentials; print('OK')`
2. `pytest tests/ -x -q`
3. `mypy harnessiq/shared/credentials.py harnessiq/providers/*/credentials.py`

## Dependencies
None

## Drift Guard
This ticket only moves credential TypedDict definitions. It must not touch the CredentialLoader, CredentialsConfig store, agent constructors, or any tool factory code.
