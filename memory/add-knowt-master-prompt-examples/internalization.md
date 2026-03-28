### 1a: Structural Survey

- Repository type: Python package with prompt and agent assets stored directly in the source tree under `harnessiq/`.
- Relevant architecture for this task:
  - Agent-specific prompts live under `harnessiq/agents/<agent>/prompts/`.
  - The Knowt agent's system prompt is sourced from `harnessiq/agents/knowt/prompts/master_prompt.md`.
  - `harnessiq/agents/knowt/agent.py` loads that Markdown file at runtime, and `tests/test_knowt_agent.py` verifies prompt loading and baseline section presence.
- Testing strategy relevant to this task:
  - `tests/test_knowt_agent.py` validates the Knowt prompt remains loadable and contains required sections such as `Agent Guide`, `Environment`, `Agent Memory`, and `Operating Rules`.
  - There is no test that pins the exact example text, so this change is primarily content-level with light regression coverage through prompt-loading tests.
- Repository conventions observed:
  - Prompt content is maintained as Markdown, not generated.
  - `memory/` contains task-scoped engineering artifacts for previous prompt changes.
  - Narrow prompt changes usually have low blast radius when they stay inside the prompt file and preserve surrounding headings.

### 1b: Task Cross-Reference

- User request: add the provided examples block to the examples section of the Knowt agent master prompt.
- Concrete codebase mapping:
  - Primary edit target: `harnessiq/agents/knowt/prompts/master_prompt.md`.
  - Verification target: `tests/test_knowt_agent.py` to ensure the prompt still loads and contains required sections after the content replacement.
- Existing behavior to preserve:
  - The Knowt prompt must remain valid Markdown text that loads from disk without code changes.
  - Existing sections such as `Recent Scripts`, `Agent Memory`, and `Operating Rules` must remain intact.
  - Existing TODO placeholders elsewhere in the file should remain because current tests expect TODO content to still exist somewhere in the prompt.
- Blast radius:
  - Limited to a single prompt file plus task artifacts under `memory/add-knowt-master-prompt-examples/`.
  - No code-path, tool, schema, or runtime behavior changes are expected.

### 1c: Assumption & Risk Inventory

- Assumption: "add these examples to the examples section" means replacing the existing placeholder TODO block under `## Example Knowt TikTok Scripts` with the provided numbered examples.
- Assumption: The examples should be inserted verbatim, including the `<Examples>` and `<Number N>` tags and the empty numbered entries.
- Assumption: No additional normalization is desired even where example text references competitor products or uses inconsistent capitalization/punctuation.
- Risk: Markdown/HTML-style angle-bracket tags could be unintentionally altered during editing. Mitigation: paste the user-provided block literally.
- Risk: Removing all TODO markers from the file would break an existing test. Mitigation: leave the other TODO sections untouched.
- Risk: The repository has unrelated untracked files under `memory/`; do not stage or modify them.

Phase 1 complete.
