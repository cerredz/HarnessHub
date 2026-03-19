## Self-Critique

- Initial implementation introduced `harnessiq/providers/apollo/requests.py` but did not actually use its builders during request preparation, which would have left an unnecessary abstraction layer in the provider package.
- Tightened `harnessiq/providers/apollo/operations.py` to route payload and query normalization through the request-builder helpers so the provider keeps a consistent layered structure with the rest of the repo.
- Re-ran the Apollo provider tests and syntax checks after this change to confirm the refactor did not regress behavior.
