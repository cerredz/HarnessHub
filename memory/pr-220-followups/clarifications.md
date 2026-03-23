# PR 220 Followups Clarifications

No blocking ambiguities remain after Phase 1.

Implementation will proceed under these explicit assumptions:

- Deliver the seven PR `#220` follow-up comments in one branch and one PR because the user asked for a single new pull request into `main`.
- Preserve public imports where practical while making the new package structure authoritative.
- Treat generated docs as derived artifacts and update them only by changing live source plus rerunning `python scripts/sync_repo_docs.py`.
