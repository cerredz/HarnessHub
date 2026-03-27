Title: Convert reusable provider-backed agent classes to DTO-first public contracts

Intent:
Move the reusable provider-backed agent families off raw payload dictionaries and onto explicit agent DTOs so the public constructor and persistence surfaces for those agents are self-documenting and stable.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/327

Scope:
- Define shared DTOs for the reusable provider-backed agent families.
- Convert the provider-backed agent bases and their concrete reusable families to consume and emit DTOs at their public boundaries.
- Update tests for the provider-backed agent families to assert on DTO contracts.
- Do not yet convert the durable-memory agents with bespoke local state; those are handled in the next ticket.

Relevant Files:
- `harnessiq/shared/dtos/agents.py` - extend with provider-backed agent DTO definitions.
- `harnessiq/agents/provider_base/agent.py` - adopt DTO-first provider-backed base contracts.
- `harnessiq/agents/apollo/agent.py` - convert Apollo reusable agent boundary to DTOs.
- `harnessiq/agents/exa/agent.py` - convert Exa reusable agent boundary to DTOs.
- `harnessiq/agents/email/agent.py` - convert Email reusable agent boundary to DTOs.
- `harnessiq/agents/instantly/agent.py` - convert Instantly reusable agent boundary to DTOs.
- `harnessiq/agents/outreach/agent.py` - convert Outreach reusable agent boundary to DTOs.
- `tests/test_provider_base_agents.py` - verify provider-backed base behavior under DTO contracts.
- `tests/test_apollo_agent.py` - verify Apollo DTO public surface.
- `tests/test_exa_agent.py` - verify Exa DTO public surface.
- `tests/test_email_agent.py` - verify Email DTO public surface.
- `tests/test_instantly_agent.py` - verify Instantly DTO public surface.
- `tests/test_outreach_agent.py` - verify Outreach DTO public surface.

Approach:
Extend the shared agent DTO module with explicit request DTOs for each reusable provider-backed family plus a stateless instance-payload DTO for families that intentionally persist no instance-specific state. The reusable family bases now accept typed request DTOs, derive the existing internal `*AgentConfig` dataclasses from those DTOs, and build a shared `ProviderToolAgentRequest` for the common provider-backed scaffold. This keeps the runtime assembly logic intact while moving the public constructor and persistence seams onto explicit contracts under `harnessiq/shared/dtos/`.

Assumptions:
- The existing shared `*AgentConfig` dataclasses remain useful as internal runtime-assembly objects even though the public constructor seam is now DTO-first.
- Reusable provider-backed agent instance identity should remain unchanged, so the new persistence DTO intentionally serializes to `{}`.
- Exporting the new request DTOs from `harnessiq.agents` is sufficient for the public SDK surface at this ticket boundary.

Acceptance Criteria:
- [x] Provider-backed reusable agents no longer expose raw dict instance payloads or equivalent raw public request boundaries.
- [x] Shared DTOs cover the reusable provider-backed agent public/persistence seams.
- [x] Existing provider-backed agent behavior remains intact under the new DTO contracts.
- [x] Focused unit tests cover DTO serialization and public constructor behavior for the reusable agent families.

Verification Steps:
- Run the provider-backed agent tests listed above.
- Run any base-agent tests affected by the changed public contracts.
- Smoke-check at least one DTO-driven provider-backed agent instantiation end to end.

Dependencies:
- Ticket 1.

Drift Guard:
This ticket stays inside the reusable provider-backed agent families. It does not broaden into the bespoke durable-memory agents, CLI adapters, or provider client DTO work.

## Quality Pipeline Results

$(cat memory/explicit-dtos-layer-boundaries/tickets/ticket-2-quality.md)

## Post-Critique Changes

$(cat memory/explicit-dtos-layer-boundaries/tickets/ticket-2-critique.md)
