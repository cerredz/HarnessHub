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
Extend the shared agent DTO module with reusable agent-family DTOs that express constructor-time and persistence-time boundaries explicitly. The provider-backed agent families are the cleanest next slice after the base instance work because their shared structure is already visible in `BaseProviderToolAgent` and the family-specific wrappers. Convert these families first so later CLI and provider tickets can target a stable DTO-based agent API instead of a moving dict-based one.

Assumptions:
- The existing shared `*AgentConfig` dataclasses remain valuable and can coexist with new DTOs where they solve different boundary problems.
- Public constructor changes are acceptable if tests and exports are updated together.
- DTO naming should prioritize boundary clarity over minimizing new types.

Acceptance Criteria:
- [ ] Provider-backed reusable agents no longer expose raw dict instance payloads or equivalent raw public request boundaries.
- [ ] Shared DTOs cover the reusable provider-backed agent public/persistence seams.
- [ ] Existing provider-backed agent behavior remains intact under the new DTO contracts.
- [ ] Focused unit tests cover DTO serialization and public constructor behavior for the reusable agent families.

Verification Steps:
- Run the provider-backed agent tests listed above.
- Run any base-agent tests affected by the changed public contracts.
- Smoke-check at least one DTO-driven provider-backed agent instantiation end to end.

Dependencies:
- Ticket 1.

Drift Guard:
This ticket must stay inside the reusable provider-backed agent families. It must not broaden into the bespoke durable-memory agents, CLI adapters, or provider client DTO work.
