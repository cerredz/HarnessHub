Title: Convert legacy service provider families to explicit DTO request and result contracts

Intent:
Apply the provider DTO pattern to the older service provider families that still rely on reflective client calls, raw payload dicts, and loose request/result transport.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/331

Scope:
- Extend the shared provider DTO module for the legacy provider families where needed.
- Convert the older service provider families and their tools to explicit DTO-first public boundaries.
- Update the corresponding provider tests to cover the new DTO behavior.
- Do not redesign provider coverage or add net-new provider operations beyond what the DTO conversion requires.

Relevant Files:
- `harnessiq/shared/dtos/providers.py` - extend DTO coverage for legacy provider families.
- `harnessiq/tools/coresignal/operations.py` - adopt DTO-first request/result transport.
- `harnessiq/tools/leadiq/operations.py` - adopt DTO-first request/result transport.
- `harnessiq/tools/peopledatalabs/operations.py` - adopt DTO-first request/result transport.
- `harnessiq/tools/phantombuster/operations.py` - adopt DTO-first request/result transport.
- `harnessiq/tools/proxycurl/operations.py` - adopt DTO-first request/result transport.
- `harnessiq/tools/salesforge/operations.py` - adopt DTO-first request/result transport.
- `harnessiq/tools/snovio/operations.py` - adopt DTO-first request/result transport.
- `harnessiq/tools/zoominfo/operations.py` - adopt DTO-first request/result transport.
- Matching `harnessiq/providers/*/client.py`, `api.py`, `requests.py`, and `operations.py` modules for those legacy families - update public request/result boundaries to use DTOs.
- `tests/test_coresignal_provider.py`, `tests/test_leadiq_provider.py`, `tests/test_peopledatalabs_provider.py`, `tests/test_phantombuster_provider.py`, `tests/test_proxycurl_provider.py`, `tests/test_salesforge_provider.py`, `tests/test_snovio_provider.py`, `tests/test_zoominfo_provider.py` - verify DTO-first behavior.

Approach:
Build on the shared provider DTOs from Ticket 5 and use them to regularize the older provider families that still move opaque dict payloads through reflective client dispatch. The goal is not to rewrite those providers into the newer architecture in one ticket; the goal is to make their public request/result seams explicit and typed so they conform to the new DTO boundary standard.

Assumptions:
- The legacy provider families can adopt DTOs without simultaneously being rewritten into the newer prepared-request architecture.
- Proxycurl remains reference-only, but its public boundary can still be typed for consistency.
- Existing endpoint coverage stays the same in this ticket.

Acceptance Criteria:
- [ ] Legacy provider families in scope stop exposing raw dict request/result contracts at their public tool/client seams.
- [ ] Shared provider DTOs cover the legacy-family transport shapes that need explicit typing.
- [ ] The legacy provider test suites continue to pass with DTO-first expectations.
- [ ] No provider loses existing endpoint behavior as a side effect of the DTO refactor.

Verification Steps:
- Run the provider test modules listed above.
- Run any shared provider-base tests impacted by the DTO conversion.
- Smoke-check at least one legacy provider tool path with a fake client/request executor.

Dependencies:
- Ticket 1.
- Ticket 5.

Drift Guard:
This ticket must stay on the legacy service-provider families. It must not expand into model-provider request builders, CLI contracts, or unrelated architecture unification.
