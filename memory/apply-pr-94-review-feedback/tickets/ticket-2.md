# Ticket 2: Generalize create_file and edit_file tool keys (remove Knowt prefix)

## Intent
`KNOWT_CREATE_FILE` and `KNOWT_EDIT_FILE` are generic file-write capabilities that happen to be wired to a memory-store base directory. Their `knowt.*` prefix implies they are Knowt-specific, but the pattern is general. Rename to `FILES_CREATE_FILE` / `FILES_EDIT_FILE` with keys `"files.create_file"` / `"files.edit_file"`.

## Scope
**Changes**: `harnessiq/shared/tools.py`, `harnessiq/tools/knowt/operations.py`, `tests/test_tools.py`, `tests/test_knowt_agent.py`
**No touch**: agent implementations, provider tools, other shared modules

## Relevant Files
- `harnessiq/shared/tools.py` — rename constants, update `__all__`
- `harnessiq/tools/knowt/operations.py` — update import names
- `tests/test_tools.py` — update constant references
- `tests/test_knowt_agent.py` — update `KNOWT_CREATE_FILE` → `FILES_CREATE_FILE` imports/refs

## Approach
Mechanical rename:
- `KNOWT_CREATE_FILE = "knowt.create_file"` → `FILES_CREATE_FILE = "files.create_file"`
- `KNOWT_EDIT_FILE = "knowt.edit_file"` → `FILES_EDIT_FILE = "files.edit_file"`
Update all imports and `__all__` entries. The tool key string changes (`knowt.create_file` → `files.create_file`) which changes the API surface.

## Acceptance Criteria
- [ ] `KNOWT_CREATE_FILE` and `KNOWT_EDIT_FILE` no longer exist in `shared/tools.py`
- [ ] `FILES_CREATE_FILE = "files.create_file"` and `FILES_EDIT_FILE = "files.edit_file"` exist
- [ ] `knowt/operations.py` uses the new constants
- [ ] All tests pass

## Dependencies
Ticket 1 (must be importable first)
