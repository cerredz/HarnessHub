### 1a: Structural Survey

- Repository type: Python SDK/package with the live runtime source rooted under `harnessiq/`.
- Bundled reusable prompts live in `harnessiq/master_prompts/prompts/` as JSON assets.
- `harnessiq/master_prompts/registry.py` discovers every `*.json` file in that package and expects `title`, `description`, and `prompt`.
- Prompt keys are derived from filenames, so adding one file registers a new prompt across the registry, CLI, and session-injection flows.
- `tests/test_master_prompts.py` is the catalog contract test and maintains an explicit expected-key set for bundled prompts.
- `artifacts/file_index.md` treats `harnessiq/` as the authoritative runtime tree and says generated docs should only be updated through `scripts/sync_repo_docs.py`.

### 1b: Task Cross-Reference

- User request: add the provided "competitor researcher" master prompt into the repository using current prompt conventions.
- Concrete mapping:
  - Add a new bundled prompt asset under `harnessiq/master_prompts/prompts/`.
  - Update `tests/test_master_prompts.py` because bundled prompt membership is explicitly asserted there.
  - No registry or CLI code changes should be required because prompt discovery is dynamic.
- Existing behavior to preserve:
  - The prompt body must remain exactly as supplied.
  - Existing bundled prompts, especially `mission_driven`, must not be overwritten.

### 1c: Assumption & Risk Inventory

- Assumption: the new key should be `competitor_researcher`, derived from the user’s label, because `mission_driven` already exists in the bundled prompt catalog with unrelated content.
- Assumption: "exactly as it is" applies to the prompt body; repository-required JSON metadata still needs a `title` and `description`.
- Risk: manual transcription into JSON could corrupt a very long prompt. Mitigation: preserve the exact body in a task-local source artifact and generate the packaged JSON from it.
- Risk: generated docs may drift if the docs generator is sensitive to the new file. Mitigation: run the docs sync check after the code change and only regenerate docs if needed.

Phase 1 complete.
