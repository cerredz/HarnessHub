# Ticket Index

1. Ticket 1: Add SDK-level search-only mode to ExaOutreachAgent
   - Introduce `search_only` in the shared config and agent constructor, branch the prompt/parameter/tool surfaces by mode, and preserve deterministic lead-only persistence.
   - Issue: `#184` — `https://github.com/cerredz/HarnessHub/issues/184`
   - Implemented: `PR #187` — `https://github.com/cerredz/HarnessHub/pull/187`

2. Ticket 2: Expose search-only mode through the outreach CLI and public docs
   - Extend CLI runtime-parameter handling and run construction for search-only mode, then update README coverage for the new SDK/CLI behavior.
   - Issue: `#185` — `https://github.com/cerredz/HarnessHub/issues/185`
   - Implemented: `PR #188` — `https://github.com/cerredz/HarnessHub/pull/188` (stacked on `PR #187`)
