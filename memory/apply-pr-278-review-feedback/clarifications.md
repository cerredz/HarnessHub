No blocking clarifications were required after Phase 1.

Working assumptions for implementation:
- The cross-agent helper refactor applies to every package in `harnessiq/agents/` that has an `agent.py` file.
- The requested refactor is organizational only: move helper logic into local/shared helper modules while preserving existing agent behavior.
- The final deliverable is one new PR to `main` that includes the Instagram ICP-rotation work plus all three pieces of review feedback from PR `#278`.
