## Self-Critique

- Initial risk: re-enabling raw Instagram tool call/result transcript entries would have solved visibility, but it would also have reintroduced noisy payloads and broken the existing low-noise harness design.
- Adjustment made: used a compact `entry_type="context"` snapshot instead. It carries only the active ICP, requested keyword, status, current recent-search window, and error text when relevant.
- Result: the context window now grows in a traceable way, while the transcript still avoids bulky search payloads and the durable `Recent Searches` parameter section remains the source of truth.
