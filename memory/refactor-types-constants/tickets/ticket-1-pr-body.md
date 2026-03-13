Title: Centralize shared type and constant definitions under `src/shared`
Issue URL: https://github.com/cerredz/HarnessHub/issues/7

Intent:
Create a single shared package for the repo’s tool- and provider-related type definitions and constants so domain modules stop defining those primitives inline. This refactor is intended to improve readability and give the codebase a clearer scaling point for cross-module definitions without changing runtime behavior.

Scope:
- Add a new `src/shared/` package.
- Move provider aliases/constants into `src/shared/providers.py`.
- Move tool aliases, dataclasses, protocols, and constants into `src/shared/tools.py`.
- Update all source modules and tests to import shared definitions from `src.shared.*`.
- Delete obsolete source files whose only responsibility was defining moved types/constants.
- Keep existing runtime behavior and test expectations intact.

Out of scope:
- Changing request payload semantics.
- Redesigning registry/provider logic beyond the import and module-boundary changes required by the refactor.
- Introducing new external tooling or build configuration.

Relevant Files:
- `src/shared/__init__.py`: package marker for shared definitions.
- `src/shared/providers.py`: canonical provider constants and aliases.
- `src/shared/tools.py`: canonical tool constants, aliases, protocols, and dataclasses.
- `src/providers/base.py`: import shared provider/tool definitions and keep provider helper logic local.
- `src/providers/__init__.py`: expose provider-facing shared definitions from the new module layout.
- `src/providers/anthropic/helpers.py`: consume shared provider/tool definitions.
- `src/providers/gemini/helpers.py`: consume shared provider/tool definitions.
- `src/providers/grok/helpers.py`: consume shared provider/tool definitions.
- `src/providers/openai/helpers.py`: consume shared provider/tool definitions.
- `src/tools/__init__.py`: expose tool-facing shared definitions from the new module layout.
- `src/tools/builtin.py`: consume shared tool definitions/constants.
- `src/tools/registry.py`: consume shared tool definitions while keeping registry behavior local.
- `tests/test_providers.py`: update imports to the new shared modules and verify behavior is unchanged.
- `tests/test_tools.py`: update imports to the new shared modules and verify behavior is unchanged.
- `src/tools/base.py`: delete after moving protocol/dataclass definitions.
- `src/tools/constants.py`: delete after moving tool constants.
- `src/tools/schemas.py`: delete after moving schema/data-model definitions.

Approach:
Create a top-level `src/shared/` package with one module per current domain boundary: `tools.py` and `providers.py`. Consolidate all non-behavioral definitions there: constants, aliases, dataclasses, and protocols. Keep runtime behavior modules where the behavior already lives: `src/tools/registry.py`, `src/tools/builtin.py`, and `src/providers/base.py` remain the places for validation and translation logic. Update all imports to point to `src.shared.*`, then remove the superseded tool definition modules so the shared package becomes the single source of truth. Retain `src.tools.__init__` and `src.providers.__init__` as curated public surfaces where it is still useful to re-export definitions.

Assumptions:
- The user-approved combined shared package should be named `src/shared/`.
- It is acceptable to change internal import paths throughout the repo to the new shared modules.
- Exceptions should remain with their behavioral modules unless they are required for correctness in the shared layer.
- The current tests are the authoritative behavioral guardrails for this refactor.

Acceptance Criteria:
- [ ] `src/shared/` exists and contains domain-specific shared modules for providers and tools.
- [ ] Provider aliases/constants are defined in `src/shared/providers.py` and no longer defined inline in `src/providers/base.py`.
- [ ] Tool constants, aliases, dataclasses, and protocols are defined in `src/shared/tools.py` and no longer defined in `src/tools/base.py`, `src/tools/constants.py`, or `src/tools/schemas.py`.
- [ ] All source modules import shared definitions from `src.shared.*`.
- [ ] Obsolete type/constant source files are removed or reduced to non-defining glue only; there are no duplicate definitions left in the old locations.
- [ ] Existing provider request-shape behavior and tool registry behavior remain unchanged.
- [ ] The test suite passes after the refactor.

Verification Steps:
1. Static analysis: if no linter is configured, document that absence and manually verify import cleanliness and unused-definition removal.
2. Type checking: if no type checker is configured, document that absence and verify Python type syntax remains valid by running the test suite.
3. Unit tests: run `python -m unittest`.
4. Integration and contract tests: document that no separate integration/contract suite exists in this repository.
5. Smoke verification: manually inspect the shared package structure and confirm provider/tool modules read from `src.shared.*` instead of local definition files.

Dependencies:
- None.

Drift Guard:
This ticket must stay a structural refactor. It must not introduce new tool/provider features, alter payload formats, rename public constant values, or redesign registry/provider logic beyond what is necessary to centralize shared definitions and update imports.


## Quality Pipeline Results
## Quality Pipeline Results

### Stage 1: Static Analysis
- No linter or static-analysis configuration is checked into the repository (`pyproject.toml`, `setup.cfg`, and `requirements.txt` are absent).
- Manual import-cleanliness check:
  - Command: `rg -n "src\.tools\.(base|constants|schemas)|src\.providers\.base import ProviderMessage|src\.tools\.schemas import ToolDefinition" src tests`
  - Result: no matches; stale imports to removed definition modules are gone.

### Stage 2: Type Checking
- No dedicated type checker is configured in the repository.
- Syntax and import validity check:
  - Command: `python -m compileall src tests`
  - Result: passed; `src/shared/` and all updated modules compiled successfully.

### Stage 3: Unit Tests
- Command: `python -m unittest`
- Result: passed.
- Output:
  - `Ran 15 tests in 0.000s`
  - `OK`

### Stage 4: Integration & Contract Tests
- No separate integration or contract test suite exists in this repository.
- Result: not applicable.

### Stage 5: Smoke & Manual Verification
- Command: inline Python smoke script importing `create_builtin_registry`, `src.shared.tools.ECHO_TEXT`, and `src.providers.openai.helpers.build_request`.
- Observed output:
  - `('core.echo_text', 'core.add_numbers')`
  - `{'role': 'system', 'content': 'Be precise.'}`
  - `echo_text`
- Confirmation:
  - Built-in registry still exposes the expected tool keys.
  - Provider request generation still prepends the system message correctly.
  - Shared tool definitions remain consumable by runtime provider helpers after the refactor.


## Post-Critique Changes
## Post-Critique Review

### Findings
1. `src/providers/base.py` still contained a local `role_map` constant inside `build_gemini_contents()`.
   - Why it mattered: the user explicitly asked for constants to live in the new shared package wherever practical.
   - Improvement: moved the Gemini role mapping into `src/shared/providers.py` as `GEMINI_ROLE_MAP`.

2. The new shared modules did not declare an explicit public surface.
   - Why it mattered: once `src/shared/` becomes the source of truth, explicit exports make the intended contract clearer for future consumers.
   - Improvement: added `__all__` declarations to `src/shared/providers.py` and `src/shared/tools.py`.

### Result
- The refactor remains structural only; no request-shape or registry behavior changed.
- Shared definitions now better match the intended “single source of truth” design for constants and typed runtime primitives.
- Post-critique verification rerun:
  - `rg -n "src\.tools\.(base|constants|schemas)|src\.providers\.base import ProviderMessage|src\.tools\.schemas import ToolDefinition" src tests` returned no matches.
  - `python -m compileall src tests` passed.
  - `python -m unittest` passed.
  - The manual smoke script still produced the expected built-in registry keys and OpenAI-style request payload shape.

