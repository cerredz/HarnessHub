# Ticket 3: Wire reasoning tools into builtin registry and update exports

## Title
Integrate `create_reasoning_tools()` into `BUILTIN_TOOLS`, expand `harnessiq/tools/__init__.py`, and update `artifacts/file_index.md`.

## Intent
Make reasoning tools available to every agent that uses the default registry by composing them into `BUILTIN_TOOLS`. Ensure the public API of `harnessiq/tools` exports the factory and all 50 constants, and document the new module in the file index.

## Scope
- **In scope**: `harnessiq/tools/builtin.py`, `harnessiq/tools/__init__.py`, `artifacts/file_index.md`.
- **Out of scope**: The reasoning module itself (Ticket 2), tests (Ticket 4).

## Relevant Files
- `harnessiq/tools/builtin.py` — import `create_reasoning_tools`, add `*create_reasoning_tools()` to `BUILTIN_TOOLS`
- `harnessiq/tools/__init__.py` — import `create_reasoning_tools` from `.reasoning` and add to `__all__`; import all 50 `REASONING_*` constants from `harnessiq.shared.tools` and re-export them
- `artifacts/file_index.md` — add entry for `harnessiq/tools/reasoning/` and `tests/test_reasoning_tools.py`

## Approach

### builtin.py
Add at the top with the other factory imports:
```python
from .reasoning import create_reasoning_tools
```
Add at the end of `BUILTIN_TOOLS`:
```python
*create_reasoning_tools(),
```

### harnessiq/tools/__init__.py
- Import `create_reasoning_tools` from `.reasoning`.
- Import all 50 `REASONING_*` constants from `harnessiq.shared.tools` (they are already imported individually — add them all).
- Add all new names to `__all__` in alphabetical order.

### artifacts/file_index.md
- Add `harnessiq/tools/reasoning/` entry in the Source layout section.
- Add `tests/test_reasoning_tools.py` entry in the Tests section.

## Assumptions
- Tickets 1 and 2 are complete.
- The `BUILTIN_TOOLS` tuple ordering doesn't matter for correctness but for readability reasoning tools should come after `create_filesystem_tools()`.

## Acceptance Criteria
- [ ] `from harnessiq.tools import create_reasoning_tools` works.
- [ ] `from harnessiq.tools import REASONING_STEP_BY_STEP` works.
- [ ] `create_builtin_registry()` includes all 50 reasoning tool keys.
- [ ] No existing tool key is displaced or shadowed.
- [ ] `artifacts/file_index.md` documents `harnessiq/tools/reasoning/` and `tests/test_reasoning_tools.py`.

## Verification Steps
1. `python -c "from harnessiq.tools import create_builtin_registry; r = create_builtin_registry(); keys = [k for k in r.keys() if k.startswith('reasoning.')]; print(len(keys))"` → `50`.
2. `python -m py_compile harnessiq/tools/builtin.py harnessiq/tools/__init__.py` → no errors.

## Dependencies
Tickets 1 and 2.

## Drift Guard
This ticket must not add or modify any tool logic, handler functions, or test files. It only wires existing code together and updates documentation.
