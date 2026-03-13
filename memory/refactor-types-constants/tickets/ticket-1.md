Title: Centralize shared type and constant definitions under `src/shared`
Issue URL: https://github.com/cerredz/HarnessHub/issues/7
PR URL: https://github.com/cerredz/HarnessHub/pull/13

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
