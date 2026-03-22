### 1a: Structural Survey

The repository is a Python 3.11+ SDK named `harnessiq` with packaged source under `harnessiq/` and lightweight documentation and architectural artifacts outside the package. The top-level package layout is stable and reflected in `artifacts/file_index.md`, which explicitly identifies `harnessiq/master_prompts/` as the curated home for deployable system prompts. Prompt assets are bundled as JSON files under `harnessiq/master_prompts/prompts/` and exposed through `harnessiq/master_prompts/registry.py`, which loads every `*.json` file in that package into a `MasterPrompt` dataclass keyed by filename.

The master prompt subsystem is intentionally simple. Each bundled prompt file contains exactly three fields: `title`, `description`, and `prompt`. There is no additional registration step beyond adding a well-formed JSON file to the prompts package. Public API access is provided through `harnessiq/master_prompts/__init__.py`, which exposes `get_prompt`, `get_prompt_text`, and `list_prompts`. Test coverage for this subsystem lives in `tests/test_master_prompts.py`, which currently verifies registry loading, key lookup, and the existing `create_master_prompts` prompt.

Existing prompt examples establish the local content conventions. `create_master_prompts.json` is a meta-prompt for producing seven-section master prompts. `prompt_architect.json` and `harness_architect.json` are longer, domain-specific behavioral contracts that use explicit section markers, high-rigor persona framing, domain-specific checklists, concrete constraints, and artifacts/inputs sections that point back to repository authority where relevant. The codebase already tolerates large prompt strings in JSON, so the correct extension mechanism is to add another bundled JSON prompt in the same style rather than inventing a new schema or loader behavior.

### 1b: Task Cross-Reference

The user asked for a new master prompt for "Creating tickets" using the existing `create_master_prompts.json` file as the structural standard and `artifacts/file_index.md` as an authoritative artifact for repository context. That maps directly onto the bundled prompt package at `harnessiq/master_prompts/prompts/`. The new asset should be a deployable system prompt whose output is a ticket artifact suitable for injection into Linear, GitHub issues, PR descriptions, or similar work-tracking surfaces.

The request also defines domain-specific output requirements that must be encoded into the prompt itself. Each generated ticket must be bounded to roughly one context window (~200k tokens), include fields such as description, intent, why, success criteria, things not to do, potential solutions, and anti-drift context like relevant files, and be written to preserve implementation clarity across software-engineering workflows. The repository artifact at `artifacts/file_index.md` is directly relevant because it describes the architectural layout and codebase standards the prompt should treat as authoritative context when identifying relevant files, module boundaries, and where new work belongs.

Concrete files touched by this change are narrow and well-bounded:

- `harnessiq/master_prompts/prompts/`: location for the new bundled master prompt JSON file.
- `tests/test_master_prompts.py`: existing validation surface for bundled prompt loading and prompt-specific smoke assertions.
- `memory/create-ticket-master-prompt/`: task-local reasoning and internalization artifacts required by the requested engineering workflow.

No registry code changes should be necessary because the loader already discovers all JSON prompt files dynamically by filename.

### 1c: Assumption & Risk Inventory

Assumption 1: The user wants a new bundled master prompt JSON artifact in `harnessiq/master_prompts/prompts/`, not merely an ad hoc prompt pasted into chat. This is strongly implied by the request to use `harnessiq/master_prompts/prompts/create_master_prompts.json`.

Assumption 2: "Creating tickets" means producing implementation-ready engineering tickets that can be pasted into Linear, GitHub issues, PR descriptions, or similar task surfaces, rather than specifically using those platforms' APIs. The prompt should therefore optimize for portable ticket content, not vendor-specific formatting.

Assumption 3: The user's requested fields ("description, intent, why, success criteria, things not to do, potential solutions, relevant files, and anti-drift context") should appear as the generated prompt's contract for ticket outputs, even if their exact capitalization or grouping is refined for prompt quality.

Risk 1: A generic ticket-writing prompt would underperform because the codebase expects prompts to be domain-specific. The prompt must therefore be explicitly about software-engineering ticket decomposition, bounded implementation scope, dependency awareness, and repository-context anchoring.

Risk 2: The "one context window" bound can drift into a vague aspiration unless translated into operational instructions. The prompt should define practical scoping heuristics such as limiting the blast radius, constraining file count when possible, requiring explicit out-of-scope boundaries, and prohibiting tickets that need full-repo mental state to implement correctly.

Risk 3: Overfitting the prompt to GitHub issue formatting would conflict with the user's requirement that tickets be injectable into Linear, GitHub issues, PRs, and similar surfaces. The prompt should produce a structured but platform-agnostic ticket artifact with strong headings and clear sections.

Phase 1 complete.
