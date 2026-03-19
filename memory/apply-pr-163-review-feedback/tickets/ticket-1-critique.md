## Self-Critique

Primary critique finding:
- The first refactor pass moved the Instagram tool definition into `harnessiq/tools` and registered it in the toolset catalog, but the agent still consumed the tool factory directly. That only partially satisfied the review comment about sourcing tools through the shared toolset.

Improvement applied:
- Updated `InstagramKeywordDiscoveryAgent` to fetch the canonical `instagram.search_keyword` definition from `harnessiq.toolset` and bind the live handler from the Instagram tool factory onto that definition before building the agent `ToolRegistry`.
- Re-ran the focused verification pipeline after that change to confirm there was no regression.

Secondary review notes:
- The Playwright provider layer stays intentionally small and generic: runtime bootstrap, Chromium context lifecycle, navigation, readiness waiting, and resilient page text/title reads. Domain-specific Google/Instagram parsing remains in the Instagram integration to avoid over-generalizing unrelated browser behavior.
- The shared Instagram constants are centralized in `harnessiq/shared/instagram.py`, which removes integration-local configuration drift without changing the CLI/backend surface.
