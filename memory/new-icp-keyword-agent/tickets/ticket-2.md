Title: Add deterministic Instagram discovery agent and Playwright search integration

Issue URL:
Blocked in local environment. `gh` cannot reach GitHub from this sandbox.

Intent:
Implement the new agent harness so it derives keyword searches from persisted ICPs, executes deterministic Google-to-Instagram search extraction through a Playwright-backed integration, refreshes context parameters after new search results are persisted, and exposes SDK-level retrieval helpers.

Scope:
- Add the new concrete agent package and prompt.
- Add a Playwright-backed search integration with explicit page/tab load waits.
- Add the deterministic internal search tool and any supporting tool-key constants.
- Add SDK-level accessors for persisted leads/emails.
- Avoid adding unrelated generic browser frameworks.

Relevant Files:
- `harnessiq/agents/instagram/__init__.py`: new agent package export.
- `harnessiq/agents/instagram/agent.py`: new concrete harness implementation.
- `harnessiq/agents/instagram/prompts/master_prompt.md`: system prompt contract.
- `harnessiq/integrations/instagram_playwright.py`: deterministic Google/Instagram search executor with load guarantees.
- `harnessiq/shared/tools.py`: new tool-key constants if needed.
- `tests/test_instagram_agent.py`: agent behavior, parameter ordering, refresh behavior, and integration seams.

Approach:
Model the harness after `ExaOutreachAgent` for deterministic tool-driven persistence and after `LinkedInJobApplierAgent` for memory-backed parameter sections and browser/runtime injection. Keep browser interaction high-level and deterministic: one search tool should own query construction, search-page loading, result opening, email extraction, persistence, and dedupe. Override or extend runtime behavior only as needed to refresh parameter sections after search-state mutations so the next cycle sees appended results.

Assumptions:
- A high-level deterministic search tool is preferable to exposing a wide manual browser tool surface.
- The agent should own only the Instagram/Google-discovery loop, not downstream verification or email sending.
- Explicit page/tab load waiting can be enforced inside the Playwright integration without changing `BaseAgent`.

Acceptance Criteria:
- [ ] A new concrete Instagram discovery agent exists and is runnable from SDK code.
- [ ] Parameter sections are ordered so ICPs appear before recent searches, and recent search results are available after search-state updates.
- [ ] The Playwright search integration explicitly waits for fully loaded search pages and opened result tabs before extraction.
- [ ] Discovered leads/emails are persisted deterministically during tool execution.
- [ ] The agent exposes SDK-level methods to retrieve persisted emails after runs.
- [ ] Tests cover parameter ordering, deterministic persistence, and load-wait integration behavior at the unit seam.

Verification Steps:
- Run targeted Instagram agent tests.
- Run any integration-mock tests for the Playwright session helpers.
- Inspect request/parameter ordering in unit tests to confirm the context contract.

Dependencies:
- Ticket 1.

Drift Guard:
This ticket must not add CLI commands, top-level command registration, or documentation-only changes beyond what is strictly required for the agent module itself. It also must not broaden into generic web crawling abstractions for the whole repo.
