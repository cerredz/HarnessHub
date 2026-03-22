# Ticket 1: Comprehensive README Rewrite

## Title
Update README.md with complete SDK documentation covering all agents, tools, providers, and CLI

## Intent
The current README is a minimal stub. It does not reflect the full capability surface of the SDK — all agent harnesses, the complete tool layer (built-ins, filesystem, reasoning, provider tools), all 14+ external service providers, master prompts, the CLI, or the config system. This ticket produces a README that a new developer can use to understand and immediately leverage any part of the SDK.

## Scope
**Changes:**
- `README.md` — complete rewrite

**Does NOT touch:**
- Any Python source files
- Tests
- Docs files (those remain as deeper references)

## Relevant Files
- `README.md` — rewritten
- `harnessiq/shared/tools.py` — source of truth for tool key constants and all tool names
- `harnessiq/providers/exa/operations.py`, `harnessiq/providers/instantly/operations.py`, etc. — operation catalogs for README tables
- `harnessiq/agents/` — agent classes for documentation
- `harnessiq/cli/linkedin/commands.py` — CLI commands for documentation
- `harnessiq/master_prompts/registry.py` — master prompts for documentation
- `docs/tools.md`, `docs/agent-runtime.md`, `docs/linkedin-agent.md` — supplement for details

## Approach
Write a structured README with clear H2 sections covering every capability layer. Use tables for providers and operations. Keep code examples minimal but runnable. Link to deeper docs for advanced usage.

## Assumptions
- The ExaOutreach agent (Ticket 3) will be documented here even though it is not yet merged — it is part of the same PR sequence. Documentation will reference `ExaOutreachAgent` as an available export.
- No new external links — only internal references to docs/ files.

## Acceptance Criteria
- [ ] Install section covers `pip install harnessiq` and `pip install -e .`
- [ ] Quick start shows the core registry/tool execution pattern
- [ ] All 4 agent classes documented (BaseAgent, BaseEmailAgent, LinkedInJobApplierAgent, KnowtAgent, ExaOutreachAgent)
- [ ] All built-in tool families documented: core, context compaction, filesystem, general-purpose (text, records, control), prompting, reasoning (3 core + brief note on 50 lenses)
- [ ] Resend email tools documented
- [ ] All 4 AI LLM providers listed (Anthropic, OpenAI, Grok, Gemini)
- [ ] All 14 external service provider tool factories documented in a table with: name, credential env var, tool key constant, operation count
- [ ] Master prompt registry usage shown
- [ ] CLI section covers all LinkedIn commands (prepare, configure, show, run, init-browser) with full flag listing
- [ ] CLI section covers all ExaOutreach commands (prepare, configure, show, run)
- [ ] Config / CredentialLoader section
- [ ] Links to docs/ for deeper reference

## Verification Steps
1. Read the completed README end to end and verify all sections are present
2. Verify every provider listed in `harnessiq/shared/tools.py` (ARCADS_REQUEST through ZOOMINFO_REQUEST) appears in the README
3. Verify every agent class exported from `harnessiq/agents/__init__.py` is documented
4. Verify all CLI sub-commands match `harnessiq/cli/linkedin/commands.py` and the new outreach commands

## Dependencies
None — standalone documentation ticket.

## Drift Guard
This ticket must not modify any Python source files, tests, or docs/ files. Changes are limited to README.md.
