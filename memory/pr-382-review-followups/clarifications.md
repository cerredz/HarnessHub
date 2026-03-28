## Clarifications

No blocking ambiguities remained after Phase 1. Implementation proceeds directly from the PR #382 review comments:

1. Centralize overlapping file-backed agent constructor logic in `BaseAgent`.
2. Move prompt-harness registered tools into the tooling layer.
3. Replace full-master-prompt stage subcalls with stage-specific prompts.
4. Expand the mission-driven durable artifact model and the tools that update it.
5. Ensure default mission-driven runs create isolated subfolders when no explicit `memory_path` is supplied.
