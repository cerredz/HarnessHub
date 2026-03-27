## Self-Critique

Initial review found one worthwhile cleanup:

- The first pass adopted `RequestPreparingClient` but left the new `client=` annotations quoted in many operation factories. Because the protocol is imported directly and the modules already use postponed annotations, those string literals added noise without value.

## Post-Critique Changes

- Normalized the patched `client=` annotations to direct `RequestPreparingClient | None` usage across the refactored operation-factory files.
- Re-ran the in-scope provider/tool regression suites and the protocol-compatible fake-client smoke check after the cleanup; all passing results were preserved.
