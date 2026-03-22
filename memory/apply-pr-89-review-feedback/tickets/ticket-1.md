# Ticket 1 — Apply PR #89 review feedback to reasoning tools

## Title
Refine reasoning tools: count presets, prose descriptions, structural fix, file index

## Intent
PR #89 was merged but the reviewer left four inline comments that require follow-up changes:
1. The `harnessiq/tools/reasoning.py` module is shadowed by the `harnessiq/tools/reasoning/` package (Python always prefers the package) — the 3-tool content must move inside the package as `reasoning/core.py`.
2. The `brainstorm` tool's `count` parameter should accept human-readable string presets (`"small"`, `"medium"`, `"large"`) in addition to raw integers.
3. Instruction output strings use bullet-point lists; the reviewer wants natural language prose in full sentences.
4. ToolDefinition `description` fields are too terse; the reviewer wants detailed, single-string natural language prose describing when to use each tool, what it does, and how its parameters work.

## Scope

**In scope:**
- Create `harnessiq/tools/reasoning/core.py` containing the 3 simple tools (brainstorm, chain_of_thought, critique) with all review improvements applied
- Update `harnessiq/tools/reasoning/__init__.py` to re-export brainstorm, chain_of_thought, critique, and create_reasoning_tools from `.core`
- Delete `harnessiq/tools/reasoning.py` (shadowed, broken)
- Remove the duplicate import on line 129 of `harnessiq/tools/__init__.py`
- Update `artifacts/file_index.md` to add entry for `harnessiq/tools/reasoning/core.py`
- Update `tests/test_reasoning_tools.py` for new count behavior

**Out of scope:**
- The 50 lens tools in `reasoning/lenses.py` — no changes
- Any other tool module
- The Knowt or other open PRs

## Relevant Files

| File | Change |
|------|--------|
| `harnessiq/tools/reasoning/core.py` | CREATE — 3-tool module with all improvements |
| `harnessiq/tools/reasoning/__init__.py` | MODIFY — add re-exports from `.core` |
| `harnessiq/tools/reasoning.py` | DELETE — shadowed by package |
| `harnessiq/tools/__init__.py` | MODIFY — remove duplicate import line 129 |
| `artifacts/file_index.md` | MODIFY — add entry for `reasoning/core.py` |
| `tests/test_reasoning_tools.py` | MODIFY — count preset tests, update boundary tests |

## Approach

**Count presets**: Add `_BRAINSTORM_COUNT_PRESETS: dict[str, int] = {"small": 5, "medium": 15, "large": 30}` and a private `_resolve_brainstorm_count()` helper that accepts `int | str`, resolves string presets, validates integer bounds. Extend `_BRAINSTORM_COUNT_MAX` to 30. Update schema `count` property to use `anyOf: [integer, string enum]` so the registry validates correctly.

**Prose descriptions (instruction output)**: Rewrite the multi-line bullet-point instruction strings as flowing, multi-sentence prose paragraphs embedded in a single joined string. Preserve all semantic content (what to produce, how many, what to include per item, final synthesis step).

**Tool descriptions (ToolDefinition.description)**: Replace the current 2–3 sentence summaries with rich, single-string descriptions that explain: what the tool does, when to call it, what parameters it accepts and why they matter, and what the agent should do with the result.

**Structural fix**: Python's import system always resolves a package (directory with `__init__.py`) before a same-named `.py` file in the same parent directory. Moving the 3-tool content into `reasoning/core.py` and re-exporting from `reasoning/__init__.py` restores the correct import path.

## Assumptions
- `_BRAINSTORM_COUNT_MIN` stays at 5 (matching "small" preset)
- `_BRAINSTORM_COUNT_DEFAULT` stays at 10
- `_BRAINSTORM_COUNT_MAX` extends to 30 (matching "large" preset)
- Passing `count=True` (bool) still raises ValueError
- An unknown preset string raises ValueError
- The registry's `anyOf` schema is handled correctly by the validation layer

## Acceptance Criteria

- [ ] `from harnessiq.tools.reasoning import brainstorm, chain_of_thought, critique` succeeds
- [ ] `from harnessiq.tools import brainstorm, chain_of_thought, critique, create_reasoning_tools` succeeds
- [ ] `brainstorm({"topic": "x", "count": "small"})` returns correct output with 5 ideas reflected
- [ ] `brainstorm({"topic": "x", "count": "medium"})` returns output with 15 ideas reflected
- [ ] `brainstorm({"topic": "x", "count": "large"})` returns output with 30 ideas reflected
- [ ] `brainstorm({"topic": "x", "count": "huge"})` raises ValueError
- [ ] `brainstorm({"topic": "x", "count": 30})` is accepted (new max)
- [ ] `brainstorm({"topic": "x", "count": 31})` raises ValueError
- [ ] No bullet-point lists appear in any instruction output
- [ ] All ToolDefinition descriptions are multi-sentence prose
- [ ] `harnessiq/tools/reasoning.py` no longer exists
- [ ] `reasoning/core.py` is listed in `file_index.md`
- [ ] All existing tests pass; new count-preset tests pass

## Verification Steps
1. `python -m py_compile harnessiq/tools/reasoning/core.py`
2. `python -m py_compile harnessiq/tools/reasoning/__init__.py`
3. `python -c "from harnessiq.tools.reasoning import brainstorm, chain_of_thought, critique, create_reasoning_tools"`
4. `python -c "from harnessiq.tools import brainstorm"`
5. `python -m unittest discover -s tests -p "test_reasoning_tools.py" -v`
6. `python -m unittest discover -s tests -v` (full suite)

## Dependencies
None — main is clean and up to date.

## Drift Guard
This ticket must not touch the 50 lens tools in `reasoning/lenses.py`, must not modify any provider modules, and must not change any Knowt-related files.
