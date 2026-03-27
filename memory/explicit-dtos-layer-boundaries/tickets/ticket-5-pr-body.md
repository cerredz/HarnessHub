Title: Introduce explicit DTOs for request-style service provider tool and client layers

Intent:
Replace the repeated raw `operation` / `path_params` / `query` / `payload` envelopes in the request-style service provider families with explicit shared provider DTOs so the provider-tool boundary is typed and self-documenting.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/330

Scope:
- Introduce shared provider DTOs for request-style service provider envelopes and results.
- Convert the request-style service provider tool factories and clients to accept/return those DTOs.
- Update the corresponding provider tests to assert against DTO-first contracts.
- Focus on the families that already follow the prepared-request pattern rather than the older legacy client families; those are handled by the next ticket.

Relevant Files:
- `harnessiq/shared/dtos/providers.py` - new shared provider request/result DTOs.
- `harnessiq/interfaces/provider_clients.py` - typed prepared-request provider client protocol.
- `harnessiq/providers/*/client.py` - request-style provider clients now accept DTO requests and emit DTO result envelopes.
- `harnessiq/providers/*/operations.py` and `harnessiq/tools/*/operations.py` - tool factories now build DTO requests and unwrap typed result envelopes.
- `tests/test_*_provider.py`, `tests/test_apollo_agent.py`, `tests/test_exa_agent.py`, `tests/test_instantly_agent.py`, `tests/test_outreach_agent.py`, `tests/test_exa_outreach_agent.py`, `tests/test_knowt_tools.py`, `tests/test_interfaces.py` - DTO-first boundary assertions.

Approach:
Added a shared provider DTO module under `harnessiq/shared/dtos/` and used it as the public contract for both prepared-request provider families and the smaller payload-dispatch families touched by this ticket. The request-style tools now construct DTOs instead of forwarding anonymous dict envelopes, the provider clients expose DTO-based `execute_operation(...)` results, and the dependent tests and protocol-compatible fake clients assert against the typed boundary directly. During verification, I also corrected an empty-query regression by preserving legacy `None` semantics at the client-to-builder adapter layer.

Assumptions:
- Shared envelope DTOs are sufficient for this ticket; provider-specific per-operation DTOs remain out of scope until a later pass proves they are needed.
- Existing provider-specific `*PreparedRequest` and `*Operation` dataclasses remain the correct internal runtime objects behind the new public DTO seam.
- Tool handlers should continue returning plain JSON-serializable dicts even though the internal contract is now DTO-based.

Acceptance Criteria:
- [x] Request-style service provider families in scope no longer pass anonymous raw request/result envelopes across their public tool/client boundaries.
- [x] Shared provider DTOs exist in `harnessiq/shared/dtos/providers.py` and are reused across the request-style families.
- [x] The provider test suites in scope are updated to assert DTO-first boundaries.
- [x] Existing prepared-request behavior and external request execution semantics remain unchanged.

Verification Steps:
- Run the provider and dependent agent/tool test modules listed in the ticket scope.
- Run package/export verification to confirm the shared DTO exports survive wheel/sdist packaging.
- Smoke-check at least one request-style provider tool end to end with a fake request executor.

Dependencies:
- Ticket 1.
- Ticket 2.
- Ticket 3.

Drift Guard:
This ticket stays with the request-style service provider families that already share the prepared-request pattern and adjacent payload-dispatch families explicitly listed in the ticket. It does not broaden into the legacy reflective client families or the model-provider SDK contracts.

## Quality Pipeline Results

$(cat memory/explicit-dtos-layer-boundaries/tickets/ticket-5-quality.md)

## Post-Critique Changes

$(cat memory/explicit-dtos-layer-boundaries/tickets/ticket-5-critique.md)
