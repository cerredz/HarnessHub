Self-critique findings:

- The biggest functional risk was relying on transcript-only tool results instead of refreshing durable parameter sections. The agent now refreshes parameters after the deterministic search tool executes.
- A wide-open browser tool surface would have made the agent less deterministic. The implementation keeps browser behavior behind one high-level search backend and one high-level tool.
- Browser lifecycle complexity was reduced by making each search execution self-contained inside the Playwright backend instead of depending on long-lived session teardown hooks in `BaseAgent`.

Post-critique changes made:

- Kept the browser API narrow and deterministic.
- Added unit coverage for the load-wait helper and Google redirect normalization.
