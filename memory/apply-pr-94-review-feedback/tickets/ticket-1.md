# Ticket 1: Fix reasoning package conflict, move numeric constants to shared, restore injectable tool exports

## Intent
`harnessiq/tools/reasoning.py` is dead code — the `reasoning/` package shadows it. The `tools/__init__.py` imports `brainstorm, chain_of_thought, critique` from the package, which fails. This makes all tests unimportable. Additionally, the numeric boundary constants for the 3 injectable reasoning tools (`_BRAINSTORM_COUNT_MIN` etc.) should live in `shared/tools.py` per PR feedback comment 4.

## Scope
**Changes**: `harnessiq/tools/reasoning/__init__.py`, `harnessiq/tools/reasoning/injectable.py` (new), `harnessiq/shared/tools.py`, `harnessiq/tools/__init__.py`, `harnessiq/tools/reasoning.py` (delete)
**No touch**: agents, knowt tools, test files (other than fixing broken imports)

## Relevant Files
- `harnessiq/tools/reasoning.py` — delete; fold content into package
- `harnessiq/tools/reasoning/injectable.py` — new; holds `brainstorm/chain_of_thought/critique` handlers + `create_injectable_reasoning_tools`; reads constants from `shared/tools.py`
- `harnessiq/tools/reasoning/__init__.py` — add exports for `brainstorm, chain_of_thought, critique, create_injectable_reasoning_tools`
- `harnessiq/shared/tools.py` — add 6 public constants: `REASON_BRAINSTORM_COUNT_MIN/MAX/DEFAULT`, `REASON_COT_STEPS_MIN/MAX/DEFAULT`
- `harnessiq/tools/__init__.py` — fix line 128 import; import from correct source

## Approach
1. Add 6 public constants to `shared/tools.py` near the existing `REASON_*` key constants
2. Create `reasoning/injectable.py` with the 3 handler functions (`brainstorm`, `chain_of_thought`, `critique`) and a `create_injectable_reasoning_tools()` factory — identical to `reasoning.py` but using the new shared constants
3. Update `reasoning/__init__.py` to also export `brainstorm, chain_of_thought, critique, create_injectable_reasoning_tools`
4. Delete `reasoning.py`
5. Fix `tools/__init__.py` line 128 to import correctly (use `create_injectable_reasoning_tools` for the 3-tool factory; keep `create_reasoning_tools` for 50-lens)

Note: The `knowt/agent.py` imports `create_reasoning_tools` from `harnessiq.tools.reasoning`. After this ticket, that resolves to the 50-lens version from `lenses.py`. The knowt agent tests expect only 3 reasoning tools (REASON_BRAINSTORM etc.). This inconsistency is addressed in Ticket 3 (KnowtAgent refactor uses `create_injectable_reasoning_tools`).

## Acceptance Criteria
- [ ] `from harnessiq.tools.reasoning import brainstorm, chain_of_thought, critique` works
- [ ] `from harnessiq.tools.reasoning import create_injectable_reasoning_tools` works
- [ ] `REASON_BRAINSTORM_COUNT_MIN/MAX/DEFAULT` and `REASON_COT_STEPS_MIN/MAX/DEFAULT` are in `shared/tools.py`
- [ ] `reasoning.py` flat file is deleted
- [ ] `from harnessiq.tools import brainstorm, chain_of_thought, critique` works
- [ ] All tests that previously imported these names now pass

## Dependencies
None
