## Summary

Reduce Instagram agent token usage by keeping the run loop driven by recent keyword memory instead of accumulated Instagram search transcript entries.

## What Changed

- Stopped carrying `instagram.search_keyword` tool calls and tool results into the next model turn.
- Suppressed blank assistant placeholder transcript entries for pure Instagram search turns.
- Added run-scoped attempted-keyword tracking so failed searches still appear in `Recent Searches`.
- Aligned the Instagram master prompt with the new low-context loop.
- Added Instagram-agent regressions and exported Instagram ledger outputs from durable memory.

## Files of Interest

- `harnessiq/agents/instagram/agent.py`
- `harnessiq/agents/instagram/prompts/master_prompt.md`
- `tests/test_instagram_agent.py`

## How To Test

1. Run `python -m compileall harnessiq/agents/instagram/agent.py tests/test_instagram_agent.py`.
2. Run `python -m pytest tests/test_instagram_agent.py`.
3. Run `python -m pytest tests/test_instagram_cli.py`.

## Risks

- Failed attempted keywords are remembered only for the active run, not durably across runs. That is intentional to avoid widening this change into a search-history schema migration.

## Linked Issues

- None
