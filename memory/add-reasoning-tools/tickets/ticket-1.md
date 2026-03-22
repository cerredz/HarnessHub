# Ticket 1: Add 50 reasoning lens key constants to harnessiq/shared/tools.py

## Title
Add 50 `REASONING_*` key constants to the shared tool constants module.

## Intent
The tool key constant file (`harnessiq/shared/tools.py`) is the single source of truth for all registered tool identifiers. Before the reasoning module can be implemented, all 50 public keys must be declared here so downstream modules can import them without circular dependencies.

## Scope
- **In scope**: Add 50 `REASONING_*` string constants and add them to `__all__`.
- **Out of scope**: Tool definitions, handlers, factory functions, tests, or registry wiring.

## Relevant Files
- `harnessiq/shared/tools.py` — add 50 constants and expand `__all__`

## Approach
Following the established pattern (`FILESYSTEM_READ_TEXT_FILE = "filesystem.read_text_file"`, etc.):
- Constant names follow `REASONING_{UPPER_SNAKE}`.
- String values follow `"reasoning.{lower_snake}"`.
- Group them in a `# Reasoning tool key constants` block, alphabetically sorted within the block.
- Append all 50 to `__all__` in the existing alphabetically-sorted list.

## Assumptions
- The `"reasoning."` domain prefix is unambiguous and not used by any existing key.
- Python identifier `80_20_focus` is renamed → constant `REASONING_PARETO_ANALYSIS = "reasoning.pareto_analysis"` (the parameter renaming happens in the tool itself).

## Acceptance Criteria
- [ ] All 50 `REASONING_*` constants are declared in `harnessiq/shared/tools.py`.
- [ ] All 50 are present in `__all__`.
- [ ] No existing constant is removed or altered.
- [ ] `from harnessiq.shared.tools import REASONING_STEP_BY_STEP` works without error.

## Verification Steps
1. `python -c "from harnessiq.shared import tools; print(len([k for k in dir(tools) if k.startswith('REASONING_')]))"` → should print `50`.
2. `python -m py_compile harnessiq/shared/tools.py` → no errors.
3. `python -m mypy harnessiq/shared/tools.py` → no type errors.

## Dependencies
None.

## Drift Guard
This ticket must not define any tool logic, handlers, schemas, or factory functions. It adds string constants only.
