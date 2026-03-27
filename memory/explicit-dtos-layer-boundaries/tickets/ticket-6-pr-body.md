Title: Convert legacy service provider families to explicit DTO request and result contracts

Intent:
Apply the provider DTO pattern to the older service provider families that still rely on reflective client calls, raw payload dicts, and loose request/result transport.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/331

Scope:
- Extend the shared provider helper surface for the legacy provider families where needed.
- Convert the older service provider families and their tools to explicit DTO-first public boundaries.
- Update the corresponding provider tests to cover the new DTO behavior.
- Address the merged PR `#383` review comment by moving the Google Drive payload helper functions into shared modules.
- Do not redesign provider coverage or add net-new provider operations beyond what the DTO conversion requires.

Relevant Files:
- `harnessiq/shared/provider_payloads.py` - shared payload parsing and reflective DTO dispatch helpers.
- `harnessiq/shared/google_drive.py` - shared Google Drive permission-payload helper moved out of the client.
- `harnessiq/providers/google_drive/client.py` and `harnessiq/providers/arxiv/client.py` - reuse the extracted shared payload helpers.
- `harnessiq/providers/coresignal/client.py`, `harnessiq/providers/leadiq/client.py`, `harnessiq/providers/peopledatalabs/client.py`, `harnessiq/providers/phantombuster/client.py`, `harnessiq/providers/proxycurl/client.py`, `harnessiq/providers/salesforge/client.py`, `harnessiq/providers/snovio/client.py`, `harnessiq/providers/zoominfo/client.py` - add DTO-backed `execute_operation(...)` seams.
- Matching `harnessiq/tools/*/operations.py` modules for those legacy families - build DTO requests instead of calling client methods directly.
- `tests/test_provider_payloads.py` plus the matching legacy provider test modules - cover the shared helper surface and DTO-first client/tool contracts.

Approach:
Reused the shared `ProviderPayloadRequestDTO` and `ProviderPayloadResultDTO` envelope types from Ticket 5 rather than introducing new DTO classes for each legacy provider family. A new shared payload helper module now owns the generic payload parsing and reflective DTO dispatch logic, which keeps the legacy clients thin while still making their public execution seam explicit. The same shared helper extraction also resolves the PR `#383` review comment by moving the general-purpose Google Drive payload helpers into `harnessiq/shared/` instead of leaving them inside the client.

Assumptions:
- The legacy provider families can adopt DTOs without being rewritten into the newer prepared-request architecture.
- `ProviderPayloadRequestDTO` / `ProviderPayloadResultDTO` are sufficient for the legacy reflective families because their transport shape is still “operation name plus kwargs payload”.
- Proxycurl remains reference-only, but its public boundary can still be typed for consistency.
- Existing endpoint coverage stays the same in this ticket.

Acceptance Criteria:
- [x] Legacy provider families in scope stop exposing raw dict request/result contracts at their public tool/client seams.
- [x] Shared provider DTOs cover the legacy-family transport shapes that need explicit typing.
- [x] The legacy provider test suites continue to pass with DTO-first expectations.
- [x] No provider loses existing endpoint behavior as a side effect of the DTO refactor.

Verification Steps:
- Run the provider test modules listed above.
- Run package/export verification after the shared helper extraction and DTO conversion.
- Smoke-check at least one legacy provider tool path with a fake client/request executor.

Dependencies:
- Ticket 1.
- Ticket 5.

Drift Guard:
This ticket stays on the legacy service-provider families and the directly related shared helper extraction requested in PR `#383`. It does not expand into model-provider request builders, CLI contracts, or unrelated provider architecture unification.

## Quality Pipeline Results

$(cat memory/explicit-dtos-layer-boundaries/tickets/ticket-6-quality.md)

## Post-Critique Changes

$(cat memory/explicit-dtos-layer-boundaries/tickets/ticket-6-critique.md)
