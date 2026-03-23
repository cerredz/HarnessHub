Title: Add the shared harness manifest types and registry

Intent: Create a single typed source of truth for stable harness metadata so future agents and custom harness integrations can import prompts, parameter schemas, memory files, provider families, and output contracts from one shared layer.

Scope:
- Add a manifest type under `harnessiq/shared/`
- Define concrete manifests for the existing harnesses
- Re-export the manifest surface from the shared package and any curated public import surface needed for SDK ergonomics
- Do not change existing harness behavior yet beyond replacing duplicated metadata/constants with manifest-backed equivalents where safe

Relevant Files:
- `harnessiq/shared/harness_manifest.py`: manifest dataclasses, coercion helpers, and validation
- `harnessiq/shared/harness_manifests.py`: manifest registry and lookup helpers
- `harnessiq/shared/*.py`: concrete harness manifests colocated with their shared constants/memory models
- `harnessiq/shared/__init__.py`: public exports
- `harnessiq/agents/__init__.py`: optional curated manifest exports for cleaner user imports

Approach:
- Model runtime/custom parameters as typed specs with generic coercion rules
- Model memory files declaratively with stable keys, paths, and formats
- Keep concrete manifests close to each harness’s shared memory/config module so the metadata stays aligned with canonical constants
- Provide a registry for manifest lookup by stable id and agent name

Assumptions:
- Existing runtime parameter helper functions stay public
- Open-ended custom parameters remain supported where current behavior allows arbitrary keys

Acceptance Criteria:
- [ ] A typed manifest layer exists under `harnessiq/shared/`
- [ ] Every current concrete harness has a manifest entry
- [ ] The manifest captures prompt path, runtime params, custom params, memory files, provider families, and output schema
- [ ] SDK users can import the manifest registry from a stable shared path

Verification Steps:
- Run targeted unit tests for the manifest helpers and any touched exports
- Import the registry and verify lookup for each current harness

Dependencies: None

Drift Guard: This ticket must not redesign agent constructors, change memory-store layouts, or change CLI persistence semantics beyond what is required to expose the new shared metadata source of truth.
