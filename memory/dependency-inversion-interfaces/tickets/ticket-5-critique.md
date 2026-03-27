## Self-Critique

- The initial refactor improved the loader seams, but `load_factory_assignment_map()` still accepted only `list[str]`, which was unnecessarily narrow for a helper that conceptually consumes generic CLI assignment sequences.
- I widened that parameter to `Sequence[str]` and updated the regression test to pass a tuple, so the helper matches the broader CLI utility conventions and remains easy to reuse from callers that do not materialize lists first.
- This keeps the contract precise without changing runtime behavior or expanding the ticket into broader CLI command work.
