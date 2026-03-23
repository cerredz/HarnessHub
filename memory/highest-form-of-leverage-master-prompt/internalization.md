### 1a: Structural Survey

The repository is a Python SDK package rooted at `harnessiq/`, with runtime code organized into clear layers:

- `harnessiq/agents/` contains concrete harnesses and shared agent runtime primitives.
- `harnessiq/tools/` contains executable tool factories and tool handlers.
- `harnessiq/providers/` contains provider adapters, HTTP clients, and external service operation catalogs.
- `harnessiq/shared/` contains shared config, schema, and durable-memory definitions.
- `harnessiq/master_prompts/` contains curated bundled prompt assets plus a small registry/API for loading them at runtime.
- `tests/` contains the regression suite for package modules, including coverage for bundled master prompts.

On `origin/main`, the bundled master prompt surface is intentionally small and file-driven:

- `harnessiq/master_prompts/prompts/*.json` are the source-of-truth prompt assets.
- `harnessiq/master_prompts/registry.py` auto-discovers `.json` files, loads `title`, `description`, and `prompt`, and exposes them through `MasterPromptRegistry`.
- `harnessiq/master_prompts/__init__.py` exposes the public retrieval API through `get_prompt`, `get_prompt_text`, and `list_prompts`.
- `tests/test_master_prompts.py` asserts registry behavior, public API behavior, and structural requirements shared by every bundled prompt.

The file index confirms the architectural boundary that matters for this task: `harnessiq/master_prompts/` is the packaged prompt asset layer, while `artifacts/` is reference documentation used to decide placement rather than the place to hand-maintain runtime files.

The project packages prompt JSON files through `pyproject.toml` via:

- `[tool.setuptools.package-data] "harnessiq.master_prompts.prompts" = ["*.json"]`

That means adding a new JSON file under the prompts package is sufficient for packaging and runtime discovery without editing setup code.

The repo also contains generated documentation artifacts, but the docs sync script builds those outputs from AST-level package structure and top-level directories. Adding a new prompt JSON file or a new task folder under `memory/` should not require artifact updates unless the generated outputs actually change.

### 1b: Task Cross-Reference

User request: create a master prompt that makes the model feel like a person combining game theory, marketing psychology, insane implementation speed, delusional optimism, and specific knowledge, then insert it into the repository and open a PR to `main`.

Concrete codebase mapping:

- `artifacts/file_index.md`
  - Input-only architectural guide. It confirms new runtime prompt assets belong under `harnessiq/master_prompts/`.
- `harnessiq/master_prompts/prompts/create_master_prompts.json`
  - Input-only structural guide. It defines the seven-section prompt format and quality bar to mirror.
- `harnessiq/master_prompts/prompts/`
  - Target directory for the new bundled prompt JSON file.
- `tests/test_master_prompts.py`
  - Needs to be updated so the new prompt is part of the expected bundled catalog and directly validated.
- `memory/highest-form-of-leverage-master-prompt/`
  - Task-local planning, ticket, quality, and critique artifacts required by the workflow.

Behavior that must be preserved:

- Registry auto-discovery must remain file-driven. No manual registration tables should be introduced.
- Public API shape must remain unchanged.
- Existing bundled prompt files and tests must continue to pass.

Blast radius:

- Low. The runtime change is additive: one new JSON asset plus test updates.
- Packaging blast radius is effectively zero because prompt JSON files are already included as package data.
- Documentation drift risk is low but must still be checked through the docs sync verification command.

### 1c: Assumption & Risk Inventory

Assumptions:

- The intended deliverable is a new bundled prompt asset, not a rewrite of `create_master_prompts.json`.
- The prompt should answer in the voice of this combined strategist/operator persona, not merely describe those attributes abstractly.
- The prompt key can be inferred from the user language rather than needing a separately approved slug.
- The PR should target `main`, but implementation must be based on `origin/main`, not the user's current dirty feature branch.

Risks:

- `origin/main` is behind local uncommitted work related to a larger prompt catalog. Accidentally building on the dirty branch would mix unrelated changes into this task.
- If the new prompt content is too generic, it would fail the standard implied by `create_master_prompts.json` even if the tests pass.
- If the prompt naming is unclear, it could create catalog churn later even though the code is functionally correct.
- GitHub workflow steps may fail if labels or repository policies differ from the workflow assumptions; that needs to be validated during issue/PR creation.

Mitigations:

- Work only inside an isolated worktree branched from `origin/main`.
- Keep the implementation additive and test-backed.
- Give the prompt a direct, statement-derived slug and a prompt-specific regression assertion.
- Validate GitHub auth and issue/PR creation commands live before finalizing.

Phase 1 complete.
