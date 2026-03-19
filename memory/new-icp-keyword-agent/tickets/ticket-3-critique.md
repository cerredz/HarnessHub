Self-critique findings:

- The highest-risk export changes were `harnessiq/agents/__init__.py` and `harnessiq/cli/main.py` because the repo already had unrelated edits there. I kept those patches minimal and additive.
- CLI ergonomics matter here because the user explicitly asked for a post-run email retrieval function. The dedicated `get-emails` subcommand keeps that surface deterministic and memory-backed.
- README updates were kept focused on the new agent rather than broad documentation churn to avoid conflicting with unrelated in-progress doc edits in the worktree.

Post-critique changes made:

- Added focused CLI coverage for `prepare`, `configure`, `show`, `run`, and `get-emails`.
- Added package smoke assertions so the new agent is part of the shipped SDK surface.
