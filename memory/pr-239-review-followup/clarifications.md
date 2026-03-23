## Clarifications

No blocking ambiguities remained after Phase 1. Implementation proceeds directly from the four review comments on PR #239:

1. Move the context binding helper out of `BaseAgent` and into the tool layer.
2. Preserve and verify opt-in-only context-tool injection.
3. Expand the context injection tool descriptions.
4. Split the context tool family into separate definition and execution layers.
