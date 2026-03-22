# Ticket 1: Reasoning Tools

## Title
Add injectable reasoning tools (`reason.*`) to the Harnessiq tool layer

## Intent
Agents need a way to trigger explicit structured reasoning before taking an action. These tools inject a `reasoning_instruction` into the agent's context window (as a normal tool result) that tells the model to output reasoning tokens — brainstorming, chain-of-thought, or critique — about a specific topic before proceeding. Any agent can include these tools in its `ToolRegistry`.

## Scope
**In scope**:
- New file `harnessiq/tools/reasoning.py` with three tools: `reason.brainstorm`, `reason.chain_of_thought`, `reason.critique`
- Three new key constants in `harnessiq/shared/tools.py`
- Re-exports in `harnessiq/tools/__init__.py`
- Full test coverage in `tests/test_reasoning_tools.py`

**Out of scope**:
- Adding reasoning tools to `BUILTIN_TOOLS` (they are opt-in per agent)
- Any LLM API calls inside tool handlers
- Changes to `BaseAgent` or the agent loop

## Relevant Files
| File | Change |
|------|--------|
| `harnessiq/tools/reasoning.py` | New — three reasoning tool implementations + `create_reasoning_tools()` factory |
| `harnessiq/shared/tools.py` | Modify — add `REASON_BRAINSTORM`, `REASON_CHAIN_OF_THOUGHT`, `REASON_CRITIQUE` constants and `__all__` entries |
| `harnessiq/tools/__init__.py` | Modify — import and re-export `create_reasoning_tools` and the three constants |
| `tests/test_reasoning_tools.py` | New — unit tests for all three tools |

## Approach

### Tool behavior
Each tool handler takes structured parameters and returns a dict with a single `reasoning_instruction` key whose value is a formatted instruction string. That string appears in the agent's transcript as a `tool_result` entry, which the model reads on the next turn and uses to guide its reasoning output.

```python
# Example output
{
    "reasoning_instruction": "[REASONING: BRAINSTORM]\nTopic: TikTok hooks\n...\nGenerate 10 ideas now. For each, provide a title and rationale."
}
```

### Tool: `reason.brainstorm`
- Key: `reason.brainstorm`
- Required: `topic` (string)
- Optional: `count` (integer, 5–25, default 10), `context` (string), `constraints` (string)
- Output: formatted brainstorm instruction block

### Tool: `reason.chain_of_thought`
- Key: `reason.chain_of_thought`
- Required: `task` (string)
- Optional: `context` (string), `steps` (integer, 3–10, default 5)
- Output: formatted step-by-step reasoning instruction block

### Tool: `reason.critique`
- Key: `reason.critique`
- Required: `content` (string)
- Optional: `aspects` (array of strings, default covers correctness/clarity/completeness)
- Output: formatted critique instruction block

### Factory function
```python
def create_reasoning_tools() -> tuple[RegisteredTool, ...]:
```
Returns all three tools as a tuple, consistent with all other `create_*_tools()` factories.

## Assumptions
- Reasoning tools are local (no API calls) — confirmed in clarifications Q1
- Tools are opt-in per agent, not added to BUILTIN_TOOLS
- Standard tool_result path handles context injection — no BaseAgent changes needed

## Acceptance Criteria
- [ ] `harnessiq/tools/reasoning.py` exists and exports `create_reasoning_tools`
- [ ] `REASON_BRAINSTORM`, `REASON_CHAIN_OF_THOUGHT`, `REASON_CRITIQUE` constants are defined in `harnessiq/shared/tools.py` and included in `__all__`
- [ ] `harnessiq/tools/__init__.py` re-exports `create_reasoning_tools` and all three constants
- [ ] All three tool handlers return a dict with a `reasoning_instruction` key
- [ ] `reason.brainstorm` formats: topic, count, context (if provided), constraints (if provided), instruction to produce N ideas with rationale
- [ ] `reason.chain_of_thought` formats: task, steps count, context (if provided), instruction to reason step-by-step
- [ ] `reason.critique` formats: content preview, aspects list, instruction to critique each aspect
- [ ] `count` for brainstorm validated to 5–25; `steps` for CoT validated to 3–10
- [ ] Invalid `count`/`steps` raises `ValueError` with a clear message
- [ ] `ToolRegistry` accepts these tools without conflicts when combined with any other tool set
- [ ] All tests pass with no linter or type errors

## Verification Steps
1. `ruff check harnessiq/tools/reasoning.py harnessiq/shared/tools.py harnessiq/tools/__init__.py`
2. `mypy harnessiq/tools/reasoning.py harnessiq/shared/tools.py`
3. `pytest tests/test_reasoning_tools.py -v --tb=short`
4. Smoke: `from harnessiq.tools import create_reasoning_tools; tools = create_reasoning_tools(); print([t.key for t in tools])`

## Dependencies
None — this is the first ticket.

## Drift Guard
This ticket must not modify `builtin.py`, `BaseAgent`, `AgentModel`, or any provider file. It must not add LLM API calls. It must not create any new agent class.
