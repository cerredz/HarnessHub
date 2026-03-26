No blocking clarifications were required after Phase 1.

Working assumptions:

- Historical run selection uses a numeric `--run N` flag on the existing resume commands.
- The default behavior remains "resume latest" when `--run` is omitted.
- Historical replay must restore the full persisted CLI payload for that run, including runtime/custom parameters.
