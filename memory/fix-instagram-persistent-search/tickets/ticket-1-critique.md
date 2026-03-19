Self-critique findings and applied improvements:

1. Cleanup ownership needed to live at the harness boundary, not only in CLI code.
Applied improvement:
- Added `InstagramKeywordDiscoveryAgent.run(...)/close()` cleanup so any closeable backend is torn down after both successful and failing runs. This keeps SDK usage and CLI usage consistent.

2. The new persistent backend behavior needed regression coverage for both success and failure paths.
Applied improvement:
- Added tests for session reuse, explicit Google-block detection, direct backend close behavior, backend close after successful runs, and backend close after model-side run failures.

3. The updated mainline base had parse-breaking merge artifacts that would have hidden the Instagram fix behind unrelated import failures.
Applied improvement:
- Repaired the broken import block in `harnessiq/providers/__init__.py` and restored the stray prune/reset logic to `BaseAgent.run()` so the Instagram command/test import path is runnable on the updated main-based worktree.

Residual risk:

- Persistent browser reuse reduces avoidable churn and matches the intended design, but it does not by itself bypass Google anti-bot controls. In this environment Google still serves a `sorry` interstitial, which is now surfaced explicitly so the next mitigation can focus on session warming, proxying, or alternate search acquisition rather than debugging silent empty results.
