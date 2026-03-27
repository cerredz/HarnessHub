## Self-Critique

- The highest risk in this refactor was breaking callers that still catch builtin exception types. The implementation avoids that by making the shared exceptions inherit from the relevant builtin families and by adding explicit compatibility assertions in tests.
- I considered extending the taxonomy into `harnessiq/agents/base/agent_helpers.py`, `harnessiq/agents/linkedin/helpers.py`, and `harnessiq/agents/prospecting/helpers.py`, but that would have expanded beyond the user’s requested “simple and small refactor for these classes.” I intentionally kept the scope on agent classes and adjacent shared exception definitions.
- I also aligned `ProviderFormatError` and `ProviderHTTPError` with the new taxonomy so the shared folder has a single exception backbone instead of parallel hierarchies.
- Residual limitation: the broader `harnessiq/shared/` model layer still raises many builtin exceptions directly. That is a separate, larger sweep and was intentionally left out of this ticket.
