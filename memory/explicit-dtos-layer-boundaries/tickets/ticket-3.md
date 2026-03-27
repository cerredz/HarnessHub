Title: Convert concrete durable-memory agents to explicit DTO contracts

Intent:
Apply the DTO boundary pattern to the concrete harness agents that currently build large raw instance payloads and expose raw dict outputs from their helpers and public entrypoints.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/328

Scope:
- Define or extend agent DTOs for the concrete harnesses with bespoke durable-memory state.
- Convert their instance-payload builders and other public boundary helpers from raw dicts to explicit DTOs.
- Update the harness tests to assert on DTO-first public contracts.
- Do not yet touch the CLI adapter surface; this ticket is about agent APIs and persistence surfaces only.

Relevant Files:
- `harnessiq/shared/dtos/agents.py` - extend with concrete harness DTOs as needed.
- `harnessiq/agents/linkedin/helpers.py` - replace raw LinkedIn instance payload dict construction with DTOs.
- `harnessiq/agents/linkedin/agent.py` - adopt DTO-first public and persistence contracts.
- `harnessiq/agents/exa_outreach/helpers.py` - replace raw ExaOutreach payload helpers with DTOs.
- `harnessiq/agents/exa_outreach/agent.py` - adopt DTO-first public and persistence contracts.
- `harnessiq/agents/knowt/helpers.py` - replace raw Knowt payload helpers with DTOs.
- `harnessiq/agents/knowt/agent.py` - adopt DTO-first public and persistence contracts.
- `harnessiq/agents/instagram/helpers.py` - replace raw Instagram payload helpers with DTOs.
- `harnessiq/agents/instagram/agent.py` - adopt DTO-first public and persistence contracts.
- `harnessiq/agents/leads/helpers.py` - replace raw Leads payload helpers with DTOs.
- `harnessiq/agents/leads/agent.py` - adopt DTO-first public and persistence contracts.
- `harnessiq/agents/prospecting/helpers.py` - replace raw Prospecting payload helpers with DTOs.
- `harnessiq/agents/prospecting/agent.py` - adopt DTO-first public and persistence contracts.
- `harnessiq/agents/research_sweep/agent.py` - adopt DTO-first public and persistence contracts.
- `tests/test_linkedin_agent.py` - verify LinkedIn DTO contracts.
- `tests/test_exa_outreach_agent.py` - verify ExaOutreach DTO contracts.
- `tests/test_knowt_agent.py` - verify Knowt DTO contracts.
- `tests/test_instagram_agent.py` - verify Instagram DTO contracts.
- `tests/test_leads_agent.py` - verify Leads DTO contracts.
- `tests/test_prospecting_agent.py` - verify Prospecting DTO contracts.
- `tests/test_research_sweep_agent.py` - verify Research Sweep DTO contracts.

Approach:
Work through the concrete harnesses that currently assemble heterogeneous dict payload snapshots and make those public/persistence boundaries explicit. The shared DTO package from Ticket 1 and the reusable-agent patterns from Ticket 2 should guide the implementation, but each durable-memory agent can keep domain-specific DTO types when the payload is genuinely domain-specific. The intent is not to flatten those domain differences; it is to stop leaking them as anonymous dictionaries.

Assumptions:
- Agent-specific DTOs can live in the shared DTO package even when their shape is specific to one harness family.
- The current durable-memory stores remain the source of truth; DTO work should wrap their boundary, not replace them wholesale.
- The user wants DTOs to be the public contract directly, so helper and constructor signatures may change.

Acceptance Criteria:
- [ ] Each concrete harness in scope has explicit DTOs for its formerly raw instance payload boundary.
- [ ] Public helper APIs in scope stop returning anonymous dict payloads where a DTO is now the boundary contract.
- [ ] The concrete harness test suites are updated to assert on DTO-first behavior.
- [ ] No harness loses existing persisted-state behavior as a side effect of the DTO conversion.

Verification Steps:
- Run the concrete harness test suites listed above.
- Run any shared/base agent tests affected by the conversion.
- Smoke-check DTO-based construction or `from_memory()` flows for at least one durable-memory harness.

Dependencies:
- Ticket 1.
- Ticket 2.

Drift Guard:
This ticket must stay in the concrete agent layer. It must not broaden into CLI adapter payload redesign or provider client/tool DTO work beyond what the agent signatures strictly require.
