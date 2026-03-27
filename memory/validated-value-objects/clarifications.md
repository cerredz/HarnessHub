No blocking clarifications were required after Phase 1.

The task is broad, but the requested direction is specific enough to proceed by:

- introducing shared validated scalar/value-object primitives under `harnessiq/shared/`
- drafting tickets for the concrete string and integer injection points found during survey
- implementing the tickets in dependency order, starting with the shared foundation and then wiring provider/config/tool call sites onto it

Follow-on ambiguities will be handled by keeping each ticket narrowly scoped and preserving public interfaces where the repo already has tests.
