Title: Centralize provider endpoint constants under `harnessiq/shared`

Intent:
Move provider endpoint/base-URL constants into `harnessiq/shared/` so provider API/client modules stop owning canonical constant values locally.

Scope:
- Establish shared provider constant definitions for provider base URLs and related immutable endpoint defaults such as API version, token URL, scope, or MIME type constants where applicable.
- Update provider `api.py`, `client.py`, and package export modules to source those values from shared modules.
- Preserve current public exports such as `DEFAULT_BASE_URL`.

Relevant Files:
- `harnessiq/shared/providers.py`: extend or supplement with canonical provider constant definitions.
- `harnessiq/providers/*/api.py`: import shared constants and retain request-building behavior.
- `harnessiq/providers/*/client.py`: continue consuming `DEFAULT_BASE_URL` through provider API/shared imports.
- Provider package `__init__.py` files that publicly re-export `DEFAULT_BASE_URL` or similar constants.
- Provider tests that assert exact default URLs or endpoint behavior.

Approach:
- Centralize only immutable provider constants in this ticket.
- Keep request-builder functions and HTTP behavior in the provider package where they already live.
- Maintain current module-level constant names in provider packages by importing from shared and re-exporting as needed.

Assumptions:
- Centralizing endpoint constants without moving behavior is sufficient to satisfy the “shared source of truth” requirement for this slice.
- `harnessiq/shared/providers.py` can hold cross-provider constants as long as the names stay explicit and non-colliding.

Acceptance Criteria:
- [ ] Provider default endpoint constants are authored in `harnessiq/shared/*`.
- [ ] Provider `api.py` modules no longer define their own canonical endpoint/base-URL constants inline.
- [ ] Public provider imports exposing `DEFAULT_BASE_URL` and similar values still work.
- [ ] Provider request-building behavior is unchanged.

Verification Steps:
1. Run syntax/import validation against touched provider/shared modules.
2. Run focused provider tests that cover moved constants and URL builders.
3. Smoke-import representative provider packages (`openai`, `anthropic`, `google_drive`, `zoominfo`) and verify their public constants still resolve.

Dependencies:
- None.

Drift Guard:
- Do not redesign request payloads or client behavior.
- Do not rename public provider constants.
- Do not mix operation metadata moves into this ticket beyond import updates strictly required by constant centralization.
