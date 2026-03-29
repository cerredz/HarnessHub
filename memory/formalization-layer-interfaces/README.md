# Formalization Layer Interfaces

## Mission

Add a minimal public formalization-layer interface surface to HarnessIQ. The target outcome is a self-documenting base formalization abstraction plus a focused subset of typed base formalization layer classes, exposed from `harnessiq.interfaces` and covered by targeted tests.

## Status

`complete`

## What Has Been Done

- Read the repository file index and the create-mission contract.
- Surveyed the `harnessiq.interfaces` package and the `BaseAgent` runtime seam.
- Confirmed the current worktree is dirty in unrelated areas and scoped this change away from those files.
- Initialized durable mission state, design notes, and the first implementation ticket.

## Key Decisions

- Keep this task at the interface layer only; do not wire formalization execution into `BaseAgent` in this change.
- Use abstract base classes rather than pure protocols because the requested design needs shared default behavior for self-documentation.

## What Was Delivered

- Added [harnessiq/interfaces/formalization.py](/C:/Users/422mi/HarnessHub/harnessiq/interfaces/formalization.py) with:
  base self-documenting formalization layer behavior,
  typed spec records,
  typed abstract bases for contracts, artifacts, hooks, stages, roles, state, and tool contributions.
- Exported the new contracts from [harnessiq/interfaces/__init__.py](/C:/Users/422mi/HarnessHub/harnessiq/interfaces/__init__.py).
- Added focused tests in [tests/test_interfaces.py](/C:/Users/422mi/HarnessHub/tests/test_interfaces.py).
- Converted [harnessiq/shared/__init__.py](/C:/Users/422mi/HarnessHub/harnessiq/shared/__init__.py) to lazy exports to eliminate a public-package import cycle exposed by the new SDK surface.

## Verification

- `python -m pytest tests/test_interfaces.py`
- `python -m pytest tests/test_output_sinks.py tests/test_toolset_dynamic_selector.py`
- `python -m pytest tests/test_harness_manifests.py tests/test_validated_shared.py tests/test_tool_selection_shared.py`

All targeted verification passed.

## Blockers / Uncertainty

No blocking ambiguity remains for the minimal interface-only version. Runtime injection into `BaseAgent` remains intentionally out of scope and is the next logical follow-up if the repository wants to activate these contracts.
