# Ticket 1 — Apply PR #92 review feedback to reasoning tools

## Title
Move reasoning constants to shared module and simplify instruction output format

## Intent
PR #92 review left two inline comments on the reasoning tools file that were not
addressed before the PR was merged. This ticket implements both:
1. The behavioral constants (_BRAINSTORM_COUNT_MIN, _BRAINSTORM_COUNT_MAX,
   _BRAINSTORM_COUNT_PRESETS, _COT_STEPS_*) belong in harnessiq/shared/ alongside
   other domain-specific shared modules (knowt.py, linkedin.py, agents.py).
2. The instruction output format should be a compact 4–5 sentence block starting with
   "You have invoked a ___ tool call." rather than multi-paragraph prose.

This work stacks on top of PR #97 (issue-96), which moves reasoning.py to
reasoning/core.py and adds count presets. The new branch is based off issue-96.

## Scope

**In scope:**
- Create `harnessiq/shared/reasoning.py` with all public behavioral constants
- Update `harnessiq/tools/reasoning/core.py` to import from shared and rewrite
  instruction outputs to the 4–5 sentence format
- Update `artifacts/file_index.md` to add shared/reasoning.py entry
- Update `tests/test_reasoning_tools.py` for format changes

**Out of scope:**
- ToolDefinition descriptions (unchanged — addressed in PR #97)
- Count presets and schema (unchanged — addressed in PR #97)
- The 50 lens tools in reasoning/lenses.py
- Any Knowt-related files

## Relevant Files

| File | Change |
|------|--------|
| `harnessiq/shared/reasoning.py` | CREATE — public behavioral constants |
| `harnessiq/tools/reasoning/core.py` | MODIFY — import from shared, rewrite instruction format |
| `artifacts/file_index.md` | MODIFY — add shared/reasoning.py entry |
| `tests/test_reasoning_tools.py` | MODIFY — update format-specific assertions |

## Approach

**Constants to shared**: Extract `BRAINSTORM_COUNT_MIN`, `BRAINSTORM_COUNT_MAX`,
`BRAINSTORM_COUNT_DEFAULT`, `BRAINSTORM_COUNT_PRESETS`, `COT_STEPS_MIN`,
`COT_STEPS_MAX`, `COT_STEPS_DEFAULT` into `harnessiq/shared/reasoning.py` as public
names (no leading underscore). Import them in `core.py` from `harnessiq.shared.reasoning`.

**Instruction format**: Replace multi-paragraph prose with a single compact block of
4–5 sentences. Template:
- brainstorm: "You have invoked a brainstorm tool call. Generate {count} distinct ideas
  on the following topic: {topic}. For each idea provide a concise title, a one-sentence
  rationale, and an estimated impact level (low, medium, or high). After generating all
  ideas, identify the strongest one and explain your selection reasoning."
  + optional context/constraints sentences.
- chain_of_thought: "You have invoked a chain-of-thought tool call. Reason through the
  following task in exactly {steps} sequential steps: {task}. For each step, state what
  aspect you are focusing on, develop your reasoning, and state a partial conclusion.
  After all {steps} steps, state your final integrated conclusion."
  + optional context sentence.
- critique: "You have invoked a critique tool call. Evaluate the following content:
  {preview}. Assess it across these aspects: {aspects}. For each aspect, describe what
  you observe, identify strengths and weaknesses, and suggest one concrete improvement.
  After completing all aspects, state the single highest-priority improvement."

Drop the [REASONING: TYPE] section header — the 4-5 sentence format is self-contained.

## Assumptions
- Constants become public (no leading underscore) since they live in shared/
- The [REASONING: TYPE] header is dropped in the new format
- Tests that check for "[REASONING: BRAINSTORM]" etc. headers will be updated to
  check for "You have invoked a brainstorm tool call" instead
- No changes to count presets or validation logic

## Acceptance Criteria

- [ ] `harnessiq/shared/reasoning.py` exists with all 6 constants + presets dict
- [ ] `reasoning/core.py` imports constants from `harnessiq.shared.reasoning`
- [ ] No `_BRAINSTORM_COUNT_MIN` or `_COT_STEPS_*` defined locally in core.py
- [ ] Each instruction output starts with "You have invoked a"
- [ ] Each instruction output is 4–5 sentences (plus optional context/constraints sentences)
- [ ] No [REASONING: TYPE] header in any instruction output
- [ ] All tests pass

## Verification Steps
1. `python -m py_compile harnessiq/shared/reasoning.py`
2. `python -m py_compile harnessiq/tools/reasoning/core.py`
3. `python -c "from harnessiq.shared.reasoning import BRAINSTORM_COUNT_MIN; print(BRAINSTORM_COUNT_MIN)"`
4. `python -m unittest discover -s tests -p "test_reasoning_tools.py" -v`
5. Spot-check instruction output for each tool by calling the handler directly

## Dependencies
Depends on PR #97 (issue-96) — the new branch is based off issue-96.

## Drift Guard
Must not touch 50-lens tools, Knowt files, or any provider modules. Must not change
the count preset values or validation bounds.
