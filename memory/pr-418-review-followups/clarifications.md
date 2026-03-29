Phase 2 was not required.

The PR comments are specific enough to implement without guessing:

- move the shared formalization record/spec types into `harnessiq/shared/`,
- split the monolithic interface module into a `harnessiq/interfaces/formalization/` package,
- deepen the default descriptive prose,
- add extensive top-of-file and per-class explanatory comments,
- and update the generated file index through `scripts/sync_repo_docs.py`.
