# Ticket 3 — Migrate arcads tool factory to `harnessiq/tools/arcads/`

## Title
Move arcads tool registry to `harnessiq/tools/arcads/`, add key constant to shared, enhance description semantics

## Intent
PR #43 feedback: same structural issue as creatify — the arcads tool registry belongs in `tools/`, not `providers/`. Additionally, the tool description should be more semantically rich to help the LLM understand when and how to use the tool.

## Scope
Same pattern as ticket 2 but for arcads.

## Relevant Files
- `harnessiq/tools/arcads/__init__.py` — **create**
- `harnessiq/tools/arcads/operations.py` — **create**: tool factory + enhanced description
- `harnessiq/providers/arcads/operations.py` — **update**: keep catalog, re-export tool factory
- `harnessiq/shared/tools.py` — **update**: add `ARCADS_REQUEST`
- `tests/test_arcads_provider.py` — **update**: import from new location

## Approach
Mirror ticket 2 for arcads. Enhanced description should explain: Arcads is an AI ad video creation platform; operations span script generation, avatar video rendering, folder/product management; lifecycle is create script → generate video → list results.

## Acceptance Criteria
- [ ] `harnessiq/tools/arcads/operations.py` contains `create_arcads_tools`
- [ ] `ARCADS_REQUEST` importable from `harnessiq.shared.tools`
- [ ] Description is semantically rich
- [ ] All arcads tests pass
- [ ] `mypy` clean

## Verification Steps
1. `python -c "from harnessiq.tools.arcads.operations import create_arcads_tools; from harnessiq.shared.tools import ARCADS_REQUEST; print('OK')"`
2. `pytest tests/test_arcads_provider.py -v`
3. `mypy harnessiq/tools/arcads/ harnessiq/providers/arcads/`

## Dependencies
None

## Drift Guard
Only arcads. Do not change operation catalog structure or HTTP behavior.
