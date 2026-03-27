Title: Introduce explicit DTOs for request-style service provider tool and client layers

Intent:
Replace the repeated raw `operation` / `path_params` / `query` / `payload` envelopes in the request-style service provider families with explicit shared provider DTOs so the provider-tool boundary is typed and self-documenting.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/330

Scope:
- Introduce shared provider DTOs for request-style service provider envelopes and results.
- Convert the request-style service provider tool factories and clients to accept/return those DTOs.
- Update the corresponding provider tests to assert against DTO-first contracts.
- Focus on the families that already follow the “prepared request” pattern rather than the older legacy client families; those are handled by the next ticket.

Relevant Files:
- `harnessiq/shared/dtos/providers.py` - new provider-boundary DTO definitions for request-style families.
- `harnessiq/tools/apollo/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/attio/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/arxiv/operations.py` - adopt provider request/result DTOs where the tool/client boundary is currently raw.
- `harnessiq/tools/browser_use/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/creatify/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/exa/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/expandi/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/google_drive/operations.py` - adopt explicit DTOs where request/result envelopes are still raw.
- `harnessiq/tools/inboxapp/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/instantly/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/lemlist/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/lusha/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/outreach/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/paperclip/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/serper/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/smartlead/operations.py` - adopt provider request/result DTOs.
- `harnessiq/tools/zerobounce/operations.py` - adopt provider request/result DTOs.
- Matching `harnessiq/providers/*/client.py` and `harnessiq/providers/*/operations.py` modules for the request-style families - update client signatures and prepared-request handoff.
- `tests/test_apollo_provider.py`, `tests/test_attio_provider.py`, `tests/test_arxiv_provider.py`, `tests/test_browser_use_provider.py`, `tests/test_creatify_provider.py`, `tests/test_exa_provider.py`, `tests/test_expandi_provider.py`, `tests/test_google_drive_provider.py`, `tests/test_inboxapp_provider.py`, `tests/test_instantly_provider.py`, `tests/test_lemlist_provider.py`, `tests/test_lusha_provider.py`, `tests/test_outreach_provider.py`, `tests/test_paperclip_provider.py`, `tests/test_serper_provider.py`, `tests/test_smartlead_provider.py`, `tests/test_zerobounce_provider.py` - verify DTO-first request/result boundaries.

Approach:
Create a shared provider DTO module for the families that already share a prepared-request pattern. Those families are the highest-leverage provider slice because they currently duplicate raw request envelopes in both tool factories and clients while already having partial explicit models like `*PreparedRequest`. Wrap the remaining raw request/result boundary in DTOs rather than inventing per-operation classes for every endpoint in this pass.

Assumptions:
- Shared envelope DTOs are sufficient for the request-style families in this ticket.
- Existing shared `*Operation` and `*PreparedRequest` dataclasses remain valid and should be reused rather than replaced.
- Final tool execution results can still be JSON-serializable after DTO conversion.

Acceptance Criteria:
- [ ] Request-style service provider families in scope no longer pass anonymous raw request/result envelopes across their public tool/client boundaries.
- [ ] Shared provider DTOs exist in `harnessiq/shared/dtos/providers.py` and are reused across the request-style families.
- [ ] The provider test suites in scope are updated to assert DTO-first boundaries.
- [ ] Existing prepared-request behavior and external request execution semantics remain unchanged.

Verification Steps:
- Run the provider test modules listed above for the families changed by the ticket.
- Run any shared provider-base tests affected by the new DTO contracts.
- Smoke-check at least one request-style provider tool end to end with a fake request executor.

Dependencies:
- Ticket 1.
- Ticket 2.
- Ticket 3.

Drift Guard:
This ticket must stay with the request-style service provider families that already share the prepared-request pattern. It must not expand into the legacy reflective client families or the model-provider SDK contracts.
