Title: Centralize provider operation metadata types under `harnessiq/shared`

Intent:
Move provider operation metadata types and catalogs into `harnessiq/shared/` so provider packages stop owning canonical dataclasses and definition-only metadata inline.

Scope:
- Move definition-only provider operation dataclasses/catalogs out of provider `operations.py` modules and into provider-specific shared modules where that metadata is reused.
- Remove any remaining duplicate request-key constants from provider `operations.py` in favor of `harnessiq/shared/tools.py`.
- Update provider operation modules, tool factories, and exports to import shared metadata.

Relevant Files:
- `harnessiq/shared/*.py`: provider-specific shared modules for non-trivial operation metadata where needed.
- `harnessiq/providers/*/operations.py`: import shared operation metadata and keep behavior-heavy request preparation/tool execution logic local.
- `harnessiq/tools/*/operations.py`: continue consuming provider operation metadata through the updated source of truth.
- Provider package `__init__.py` files that export operation dataclasses/catalog helpers.
- Tests covering provider operation catalogs and tool-definition generation.

Approach:
- Split metadata from behavior.
- Keep catalog dataclasses, prepared-request dataclasses, and immutable catalogs in shared modules.
- Keep request-building, client coercion, and tool execution handlers in provider/tool modules.
- Use existing `shared/tools.py` request-key constants as the only authoritative source of provider request tool keys.

Assumptions:
- Operation metadata classes are part of the requested “types/constants” surface because they are definition-only and are reused by provider and tool modules.
- Provider-specific shared modules are preferable to turning `shared/providers.py` into a monolith.

Acceptance Criteria:
- [ ] Provider operation metadata types and catalogs live in `harnessiq/shared/*`.
- [ ] Provider operation modules no longer define duplicate request-key constants that already exist in `harnessiq/shared/tools.py`.
- [ ] Provider/tool modules import operation metadata from shared modules.
- [ ] Public provider exports for operation metadata continue to work.
- [ ] Operation-catalog and tool-surface tests continue to pass.

Verification Steps:
1. Run syntax/import validation against touched shared/provider/tool modules.
2. Run focused provider tests for operation catalogs and tool-definition factories.
3. Smoke-import representative providers/tools that depend on shared operation metadata.

Dependencies:
- Ticket 2 is complementary but not strictly blocking.

Drift Guard:
- Do not rewrite provider request execution behavior.
- Do not change operation names, summaries, or tool-key values.
- Do not move generic tool runtime dataclasses out of `harnessiq/shared/tools.py`.
