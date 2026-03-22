### 1a: Structural Survey

**Stack**: Python 3.11+, setuptools, no linter config in pyproject.toml. Test runner is `unittest` (standard library).

**Relevant modules for this task**:
- `harnessiq/agents/base.py` — `BaseAgent` abstract class; `__init__` accepts `name, model, tool_executor, runtime_config`; no memory-store concept
- `harnessiq/agents/knowt/agent.py` — `KnowtAgent(BaseAgent)`; hardcodes tool creation in constructor; defines `_PROMPTS_DIR`/`_MASTER_PROMPT_PATH` module-level constants
- `harnessiq/shared/tools.py` — all tool key string constants + runtime data models (`ToolDefinition`, `RegisteredTool`, etc.)
- `harnessiq/shared/knowt.py` — `KnowtMemoryStore`, `KnowtAgentConfig`, filename constants (`CURRENT_SCRIPT_FILENAME`, etc.)
- `harnessiq/shared/agents.py` — `AgentRuntimeConfig`, `DEFAULT_AGENT_MAX_TOKENS`, etc.
- `harnessiq/tools/reasoning.py` — 3-tool injectable reasoning module with `brainstorm/chain_of_thought/critique` handlers + numeric constants `_BRAINSTORM_COUNT_MIN/MAX/DEFAULT`, `_COT_STEPS_MIN/MAX/DEFAULT` **(DEAD CODE — shadowed by reasoning/ package)**
- `harnessiq/tools/reasoning/__init__.py` — 50-lens reasoning package; exports `create_reasoning_tools` from `lenses.py` + all REASONING_* constants; does NOT export `brainstorm/chain_of_thought/critique`
- `harnessiq/tools/reasoning/lenses.py` — 50 cognitive lens tool implementations
- `harnessiq/tools/knowt/operations.py` — 5 Knowt tools; uses `KNOWT_CREATE_FILE`, `KNOWT_EDIT_FILE` keys
- `harnessiq/tools/__init__.py` — broken line 128: `from .reasoning import brainstorm, chain_of_thought, create_reasoning_tools, critique` fails because the package doesn't export those functions

**Pre-existing bug**: `harnessiq/tools/__init__.py:128` imports `brainstorm, chain_of_thought, critique` from the reasoning package, which doesn't export them. This was introduced when the `reasoning/` package was added (shadowing `reasoning.py`) without updating the import. All tests currently fail to import.

### 1b: Task Cross-Reference

| PR Comment | Location | Action |
|---|---|---|
| Constants to shared | `agent.py:24` `_PROMPTS_DIR`, `_MASTER_PROMPT_PATH` | Add `PROMPTS_DIRNAME`, `MASTER_PROMPT_FILENAME` to `shared/knowt.py`; import them in `agent.py` |
| Memory store in base, tools/config as params | `agent.py:38` KnowtAgent `__init__` | Add `memory_path` param to `BaseAgent.__init__`; add optional `tools: Sequence[RegisteredTool]` and `config: KnowtAgentConfig` to `KnowtAgent.__init__`; update tests |
| create_file tool should be general | `shared/tools.py:47` `KNOWT_CREATE_FILE` | Rename to `FILES_CREATE_FILE = "files.create_file"` (and `KNOWT_EDIT_FILE` → `FILES_EDIT_FILE`); update all references |
| Constants to shared | `reasoning.py:15` `_BRAINSTORM_COUNT_MIN` etc. | Move to `shared/tools.py`; fix `reasoning.py` → package conflict; export `brainstorm/chain_of_thought/critique` from package; fix broken `tools/__init__.py` import |

### 1c: Assumption & Risk Inventory

1. `reasoning.py` is dead (shadowed by `reasoning/` package). Moving its constants to shared also requires either folding its content into the package or making the package re-export those functions. Both the `tools/__init__.py` import and `tests/test_reasoning_tools.py:554` import `brainstorm, chain_of_thought, critique` from the package — these need to be fixed.

2. For Comment 2 (tools/config as params): making `tools` required would break tests. Making it optional with default None → build defaults internally is the compatible approach. The user's intent is "ability to inject" — optional parameter with sensible default is sufficient.

3. `KNOWT_EDIT_FILE` is logically paired with `KNOWT_CREATE_FILE` — both should be renamed together for consistency, even though the comment only mentioned create_file.

4. Tests reference `from harnessiq.agents.knowt.agent import _MASTER_PROMPT_PATH` — after moving the constant string to shared, `_MASTER_PROMPT_PATH` stays as a module-level Path in `agent.py` (path construction using `__file__` must stay there); tests can keep importing `_MASTER_PROMPT_PATH`.

Phase 1 complete.
