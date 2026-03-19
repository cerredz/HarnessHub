No blocking user clarifications are required after Phase 1.

Implementation assumptions chosen to keep the task additive and consistent with repo patterns:

1. The new agent domain will be `instagram`, with a concrete SDK harness focused on deriving keyword searches from persisted ICP descriptions and executing deterministic Google `site:instagram.com` searches.
2. ICP input will be persisted as a list of strings in agent memory and exposed through both SDK construction parameters and CLI configuration.
3. Browser work will be executed through a new Playwright-backed integration with explicit load waits for the search page and each opened result tab before extraction.
4. Canonical persistent state will include a durable JSON file for discovered leads/emails, plus JSON search-history state used to populate the context window.
5. The SDK/CLI `get-emails` surface will return persisted discovered emails across runs; per-run filtering can be added later without changing the base storage contract.
