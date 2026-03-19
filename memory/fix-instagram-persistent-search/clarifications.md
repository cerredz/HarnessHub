Phase 2 not required.

The user request is specific enough to proceed without blocking clarification:

- The Instagram agent should keep one persistent browser session alive across repeated keyword searches in a run.
- The Playwright provider/integration layer should support that lifecycle directly instead of recreating the browser per search.
- Search failures caused by Google interstitial blocking should be surfaced clearly rather than silently stored as empty results.
