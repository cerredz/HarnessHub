Title: Convert model-provider SDK surfaces to DTO-first request contracts and export them publicly

Intent:
Replace the raw dict/list request shapes in the OpenAI, Anthropic, Gemini, and Grok provider SDK surfaces with explicit DTOs and wire those DTOs into the public package exports and tests.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/332

Scope:
- Introduce shared/model-provider DTOs for the SDK request boundaries.
- Convert model-provider request builders and thin clients to DTO-first public APIs.
- Update package exports and packaging tests so DTOs are part of the public contract directly.
- Keep the underlying HTTP behavior and endpoint coverage stable.

Relevant Files:
- `harnessiq/shared/dtos/providers.py` - extend with model-provider DTO definitions.
- `harnessiq/shared/providers.py` - update shared provider aliases/types to align with DTO-first contracts.
- `harnessiq/providers/base.py` - replace raw provider message/request helpers with DTO-aware helpers.
- `harnessiq/providers/openai/client.py` - adopt DTO-first public request contracts.
- `harnessiq/providers/openai/requests.py` - consume DTOs in request builders.
- `harnessiq/providers/anthropic/client.py` - adopt DTO-first public request contracts.
- `harnessiq/providers/anthropic/messages.py` - consume DTOs in request builders.
- `harnessiq/providers/gemini/client.py` - adopt DTO-first public request contracts.
- `harnessiq/providers/gemini/content.py` - consume DTOs in request builders.
- `harnessiq/providers/grok/client.py` - adopt DTO-first public request contracts.
- `harnessiq/providers/grok/requests.py` - consume DTOs in request builders.
- `harnessiq/providers/__init__.py` - export the DTO-first provider surface appropriately.
- `harnessiq/shared/__init__.py` - export provider DTOs from the shared surface where appropriate.
- `tests/test_openai_provider.py`, `tests/test_anthropic_provider.py`, `tests/test_gemini_provider.py`, `tests/test_grok_provider.py`, `tests/test_provider_base.py`, `tests/test_sdk_package.py` - verify DTO-first public contracts and exports.

Approach:
Use the shared provider DTO module to model the public request boundaries for the model-provider SDK surfaces. These clients are currently thin wrappers over raw dict/list builders; this ticket makes those public contracts explicit and then updates the package exports and tests so the DTOs are first-class public API rather than internal implementation details. The final emitted HTTP payloads can remain dictionaries, but DTOs should own the boundary above that translation.

Assumptions:
- The user wants DTOs to be the public contract directly, so changing these public provider client signatures is acceptable.
- The canonical provider message/request abstractions should move toward DTOs instead of `TypedDict`-style aliases.
- The package tests should be updated to lock in the new DTO-based public surface.

Acceptance Criteria:
- [ ] OpenAI, Anthropic, Gemini, and Grok client/request-builder public APIs use explicit DTOs instead of raw dict/list payloads.
- [ ] Shared provider DTOs cover the model-provider request boundaries.
- [ ] Public exports and packaging tests reflect DTOs as first-class public SDK contract types.
- [ ] Existing HTTP request payload behavior remains stable after DTO translation.

Verification Steps:
- Run the model-provider test modules listed above.
- Run `tests/test_provider_base.py`.
- Run `tests/test_sdk_package.py`.
- Smoke-check at least one DTO-driven request build for each model-provider family with fake request executors.

Dependencies:
- Ticket 1.
- Ticket 5.
- Ticket 6.

Drift Guard:
This ticket must stay focused on model-provider SDK request contracts and public exports. It must not reopen completed agent, CLI, or service-provider ticket scope except for import adjustments required by the new DTO exports.
