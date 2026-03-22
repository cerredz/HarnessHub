Post-implementation critique findings:

1. The first implementation proved the context block was smaller, but it did not explicitly test the exact comma-separated multi-keyword format the user requested.
   Change made:
   - Added `test_recent_searches_are_rendered_as_comma_separated_keywords` in `tests/test_instagram_agent.py`.
   - Extended the direct tool-execution tests to assert both searched and duplicate responses remain compact and do not include `query` or `visited_urls`.

2. Residual design debt remains around `recent_result_window`.
   Assessment:
   - This runtime parameter is now effectively unused by the Instagram agent context window.
   - Removing it would widen scope into runtime compatibility and CLI behavior, so it was intentionally left untouched for this ticket.

3. Repository baseline issues remain outside ticket scope.
   Assessment:
   - The current `main` branch fails Instagram test imports earlier in shared provider initialization because `harnessiq/shared/http.py` uses `@dataclass` without importing it.
   - This PR does not change that unrelated provider/import problem.

Follow-up result:
- The added assertions remain in the PR branch and compile cleanly against the updated `main`-based implementation.
