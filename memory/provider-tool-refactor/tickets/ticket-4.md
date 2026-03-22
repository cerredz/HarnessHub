# Ticket 4 — Migrate exa, instantly, lemlist, outreach tool factories to `harnessiq/tools/`

## Title
Move exa, instantly, lemlist, and outreach tool registries to `harnessiq/tools/{name}/`, add key constants to shared, enhance descriptions

## Intent
PR #44 feedback: same structural pattern as tickets 2 and 3 but applied to the four providers merged in that PR. Each gets its own subfolder in `tools/`.

## Scope
- Create `harnessiq/tools/{exa,instantly,lemlist,outreach}/` with `__init__.py` + `operations.py`
- Move tool factories out of `providers/{name}/operations.py` into the new locations
- Add `EXA_REQUEST`, `INSTANTLY_REQUEST`, `LEMLIST_REQUEST`, `OUTREACH_REQUEST` to `shared/tools.py`
- Re-export shims in provider operations.py files
- Update test imports

## Relevant Files
- `harnessiq/tools/exa/__init__.py`, `operations.py` — **create**
- `harnessiq/tools/instantly/__init__.py`, `operations.py` — **create**
- `harnessiq/tools/lemlist/__init__.py`, `operations.py` — **create**
- `harnessiq/tools/outreach/__init__.py`, `operations.py` — **create**
- `harnessiq/providers/{exa,instantly,lemlist,outreach}/operations.py` — **update**: keep catalog, add re-export
- `harnessiq/shared/tools.py` — **update**: 4 new key constants
- `tests/test_{exa,instantly,lemlist,outreach}_provider.py` — **update**: imports

## Enhanced descriptions:
- **exa**: Exa is a web search and content retrieval API. Operations: neural/keyword search, full content fetch, find similar pages, AI-generated answers, Websets management.
- **instantly**: Instantly is a cold email outreach automation platform. Operations span account management, campaign lifecycle, lead tracking, inbox monitoring, analytics.
- **lemlist**: Lemlist is a multi-channel outreach platform. Operations cover campaign management, lead lifecycle, team settings, enrichment, inbox, webhooks.
- **outreach**: Outreach is a B2B sales engagement platform. Operations cover prospect/account CRM, sequences, calls, tasks, mailboxes, and pipeline management.

## Acceptance Criteria
- [ ] All four providers have `harnessiq/tools/{name}/operations.py` with `create_{name}_tools`
- [ ] All four key constants in `harnessiq/shared/tools.py`
- [ ] All provider test files pass
- [ ] `mypy` clean across all four

## Verification Steps
1. Import check for each provider tool factory and key constant
2. `pytest tests/test_exa_provider.py tests/test_instantly_provider.py tests/test_lemlist_provider.py tests/test_outreach_provider.py -v`
3. `mypy harnessiq/tools/exa harnessiq/tools/instantly harnessiq/tools/lemlist harnessiq/tools/outreach`

## Dependencies
None

## Drift Guard
Only the four named providers. Do not restructure catalogs or change HTTP behavior.
