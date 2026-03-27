Title: Add shared validated scalar value objects

Issue URL: https://github.com/cerredz/HarnessHub/issues/335

Intent:
Establish a reusable shared layer for validated primitive-like values so the repository can stop scattering blank-string and integer-bound checks across dataclasses, parsers, and tool handlers. This is the foundation for the rest of the refactor.

Scope:
Create shared validated scalar/value-object primitives under `harnessiq/shared/` for the string and integer concepts already repeated throughout the codebase, and add focused unit coverage for their construction and failure modes. This ticket does not yet rewire provider credentials, context tools, or provider operation descriptions onto the new types.

Relevant Files:
- `harnessiq/shared/validated.py`: new shared validated scalar/value-object primitives and parse helpers
- `harnessiq/shared/__init__.py`: export the new shared validation surface where appropriate
- `tests/test_validated_shared.py`: focused unit tests for valid and invalid scalar construction

Approach:
Introduce a small set of immutable validated scalars that preserve compatibility by behaving like normalized values at the boundary while making invalid construction impossible. The initial set should cover non-empty trimmed strings, env-variable names, provider-family identifiers, HTTP/HTTPS base URLs, non-negative integers, strictly positive integers, and bounded integer parsing helpers. Prefer explicit constructors or parse methods over implicit magic. Keep the API small and composable so higher-level modules can use semantic wrappers without inheriting unnecessary coupling.

Assumptions:
- Shared validated scalars belong under `harnessiq/shared/` because they are cross-cutting runtime primitives.
- These types should normalize inputs eagerly and fail at construction time with clear `ValueError` messages.
- Compatibility is best preserved by exposing `.value`-style access and/or string/int conversion helpers rather than forcing immediate annotation changes across the repo.

Acceptance Criteria:
- [ ] A new shared validated-scalar module exists under `harnessiq/shared/`.
- [ ] The module includes reusable constructors/parsers for non-empty strings, env-variable names, provider-family identifiers, HTTP/HTTPS URLs, non-negative integers, and strictly positive integers.
- [ ] Invalid values fail during construction with clear error messages.
- [ ] New unit tests cover happy paths, normalization behavior, and representative failures.

Verification Steps:
- Run the new validated-scalar test module.
- Run import smoke tests to confirm the new shared module is packaged and importable.
- Manually exercise representative constructors in a Python shell if needed.

Dependencies:
- None

Drift Guard:
This ticket must not refactor repository call sites yet. It creates the shared foundation only and avoids broad churn before the value-object API is stable.
