# Ticket 5: File Index Update

## Title
Update `artifacts/file_index.md` to reflect all new modules from tickets 1–4

## Intent
`file_index.md` is the canonical repository map. Every new directory and meaningful file added by this task must be documented there to keep the index accurate.

## Scope
**In scope**: Updates to `artifacts/file_index.md` only.
**Out of scope**: Everything else.

## Relevant Files
| File | Change |
|------|--------|
| `artifacts/file_index.md` | Modify — add new source layout entries, test entries |

## Approach
Add the following to the **Source layout** section:
- `harnessiq/tools/reasoning.py`: injectable reasoning tools (`reason.brainstorm`, `reason.chain_of_thought`, `reason.critique`) for structured reasoning prompt injection
- `harnessiq/tools/knowt/`: MCP-style tool factory for Knowt content creation pipeline (create_script, create_avatar_description, create_video via Creatify, create_file, edit_file)
- `harnessiq/agents/knowt/`: Knowt TikTok content creation agent harness
- `harnessiq/agents/knowt/prompts/`: system prompt files for the Knowt agent
- `harnessiq/shared/knowt.py`: `KnowtMemoryStore`, `KnowtAgentConfig`, `KnowtCreationLogEntry`, and filename constants

Add to the **Tests** section:
- `tests/test_reasoning_tools.py`: coverage for reasoning tool implementations and instruction formatting
- `tests/test_knowt_tools.py`: coverage for Knowt tool handlers, memory guard enforcement, and Creatify integration
- `tests/test_knowt_agent.py`: coverage for the Knowt agent harness, prompt loading, parameter sections, and tool wiring

Add to **Current memory artifacts**:
- `memory/knowt-agent/`: internalization, clarification, ticket, quality, and critique artifacts for the reasoning tools and Knowt agent work

## Dependencies
Tickets 1–4 must be implemented before this is accurate.

## Drift Guard
This ticket must only modify `artifacts/file_index.md`. No source code changes.
