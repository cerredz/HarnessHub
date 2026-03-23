## Declarative Harness Manifest Internalization

### 1a: Structural Survey

- `harnessiq/agents/` contains the concrete harnesses and the shared `BaseAgent` runtime. Each concrete harness currently hard-codes its prompt path, runtime defaults, instance payload shape, and memory-store contract.
- `harnessiq/shared/` is the correct architectural home for reusable typed definitions, memory-store file constants, and cross-agent metadata. The file index explicitly says shared configs/constants belong here rather than inline in agent modules or CLIs.
- `harnessiq/cli/` contains one command module per harness. The CLI layer currently duplicates supported runtime parameter tuples, value coercion, help text, and in some cases file-name knowledge.
- `artifacts/file_index.md` is the repository architecture map and needs to document any new shared boundary.
- `tests/` already covers agent constructors, CLI runtime parameter normalization, and shared runtime behavior. A new manifest layer belongs under direct unit coverage.

### 1b: Task Cross-Reference

User request: implement a declarative typed harness manifest that captures stable harness metadata including name, prompt path, runtime params, custom params, memory files, provider families, and output schema; put the type in `harnessiq/shared/`; reduce CLI boilerplate; update `artifacts/file_index.md`.

Concrete code paths touched by that request:

- Shared metadata/type layer:
  - `harnessiq/shared/` for the new manifest types and shared registry
  - agent-specific shared modules (`shared/linkedin.py`, `shared/instagram.py`, `shared/prospecting.py`, `shared/leads.py`, `shared/knowt.py`, `shared/exa_outreach.py`) for concrete manifests
- CLI integration:
  - `harnessiq/cli/common.py`
  - `harnessiq/cli/linkedin/commands.py`
  - `harnessiq/cli/instagram/commands.py`
  - `harnessiq/cli/prospecting/commands.py`
  - `harnessiq/cli/leads/commands.py`
  - `harnessiq/cli/exa_outreach/commands.py`
- Public import surface:
  - `harnessiq/shared/__init__.py`
  - optionally `harnessiq/agents/__init__.py` for cleaner user-facing imports
- Documentation:
  - `artifacts/file_index.md`
  - `docs/agent-runtime.md`
- Verification:
  - existing CLI tests that assert supported runtime parameter behavior
  - a new manifest-focused test module

Current gaps relative to the request:

- There is no typed cross-agent manifest concept today.
- Runtime/custom parameter specs live in scattered tuples/functions rather than one declarative source of truth.
- Memory-file knowledge is spread across store classes and CLI modules.
- Users importing harness metadata have no unified registry.

### 1c: Assumption & Risk Inventory

Assumptions:

- The manifest should be additive and backward-compatible rather than a redesign of agent constructors or memory-store layouts.
- Existing public helper functions like `normalize_linkedin_runtime_parameters()` should remain available, but they can delegate to the manifest.
- “Output schema” is best represented as the structured run-output contract each harness exposes today, primarily the ledger output shape where available.
- “Cleaner custom-harness imports” means users should be able to import manifest metadata from one shared registry or curated export surface.

Risks:

- Several harnesses do not currently validate custom params the same way; the manifest layer needs to support both typed specs and open-ended custom-parameter maps.
- Leads and ExaOutreach persist runtime-like values differently from the other agents, so the first refactor should centralize typing/coercion without forcing a storage-layout rewrite.
- The repo already has unrelated uncommitted changes, so edits must stay tightly scoped and avoid touching user work.

Clarification status:

- No blocking ambiguities remain. The work can proceed as an additive shared metadata layer plus CLI/runtime integration.

Phase 1 complete.
