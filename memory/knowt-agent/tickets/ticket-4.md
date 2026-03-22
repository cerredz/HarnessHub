# Ticket 4: Knowt Agent Harness

## Title
Add `KnowtAgent` harness under `harnessiq/agents/knowt/` with file-based master prompt

## Intent
The Knowt agent is a concrete `BaseAgent` subclass that wires together the reasoning tools, Knowt tools, `KnowtMemoryStore`, and a file-loaded master prompt. The system prompt lives in a separate `.md` file so it can be updated without touching Python code.

## Scope
**In scope**:
- `harnessiq/agents/knowt/__init__.py`
- `harnessiq/agents/knowt/agent.py` — `KnowtAgent` class
- `harnessiq/agents/knowt/prompts/master_prompt.md` — system prompt with TODO placeholders
- Update `harnessiq/agents/__init__.py` to export `KnowtAgent` and `KnowtMemoryStore`
- Test coverage in `tests/test_knowt_agent.py`

**Out of scope**:
- CLI commands for the Knowt agent
- Credentials loading (caller's responsibility)
- Actual Vidbyte content (TODOs in prompt file)

## Relevant Files
| File | Change |
|------|--------|
| `harnessiq/agents/knowt/__init__.py` | New — re-exports |
| `harnessiq/agents/knowt/agent.py` | New — `KnowtAgent` implementation |
| `harnessiq/agents/knowt/prompts/master_prompt.md` | New — prompt template with TODO sections |
| `harnessiq/agents/__init__.py` | Modify — add `KnowtAgent`, `KnowtMemoryStore` to imports and `__all__` |
| `tests/test_knowt_agent.py` | New — harness tests |

## Approach

### Directory structure
```
harnessiq/agents/knowt/
├── __init__.py
├── agent.py
└── prompts/
    └── master_prompt.md
```

### KnowtAgent constructor
```python
class KnowtAgent(BaseAgent):
    def __init__(
        self,
        *,
        model: AgentModel,
        memory_path: str | Path,
        creatify_client: CreatifyClient | None = None,
        creatify_credentials: CreatifyCredentials | None = None,
        max_tokens: int = DEFAULT_AGENT_MAX_TOKENS,
        reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD,
    ) -> None:
```
- Constructs `KnowtMemoryStore(memory_path=...)`
- Calls `KnowtMemoryStore.prepare()`
- Builds `ToolRegistry` from: `create_reasoning_tools()` + `create_knowt_tools(memory_store=..., creatify_client=..., creatify_credentials=...)`
- Passes `runtime_config=AgentRuntimeConfig(max_tokens=..., reset_threshold=...)` to `super().__init__`

### build_system_prompt
- Loads `harnessiq/agents/knowt/prompts/master_prompt.md` at call time (relative to the Python module's `__file__`)
- Returns the file contents as the system prompt
- Raises `FileNotFoundError` with a clear message if the file is missing

### load_parameter_sections
Returns two sections:
1. `AgentParameterSection(title="Current Script", content=memory_store.read_script() or "(no script created yet)")`
2. `AgentParameterSection(title="Current Avatar Description", content=memory_store.read_avatar_description() or "(no avatar description created yet)")`

### prepare
Calls `memory_store.prepare()`.

### master_prompt.md structure
```markdown
# Knowt TikTok Content Creation Agent

## Agent Guide
[Description of what this agent is and how it operates]

## Environment
[Available tools and how they compose: reason.brainstorm → create_script → create_avatar_description → create_video]

## Vidbyte Background
[TODO: Add Vidbyte company background here]

## Common Pain Points
[TODO: Add Vidbyte/Knowt common customer pain points here]

## Ideal Customer Profile (ICP)
[TODO: Add ICP definition here]

## Example Knowt TikTok Scripts
[TODO: Add 2-3 example TikTok scripts here]

## Recent Scripts
[TODO: Add recently created scripts here — updated by the agent via create_file/edit_file]

## Agent Memory
The agent tracks creation state in its memory store. Before calling create_video, both create_script and create_avatar_description must be called in that order. Calling create_video without completing these steps will return a descriptive error.

## Operating Rules
- Always call reason.brainstorm before create_script to generate ideas first
- Always call create_avatar_description after create_script and before create_video
- Use create_file and edit_file to persist notes and draft content to memory
- If create_video returns an error about missing prerequisites, complete the missing steps first
```

## Assumptions
- Master prompt is loaded from a path relative to `agent.py`'s `__file__` — works after pip install
- Reasoning tools + Knowt tools are sufficient; no additional browser or email tools needed
- `prepare()` is called in the constructor AND overridden in the `prepare()` method for `BaseAgent.run()` compatibility

## Acceptance Criteria
- [ ] `harnessiq/agents/knowt/` directory with all four files
- [ ] `KnowtAgent` successfully instantiates with only `model` and `memory_path`
- [ ] `build_system_prompt()` returns the content of `master_prompt.md`
- [ ] `load_parameter_sections()` returns two sections with current script and avatar description content
- [ ] `available_tools()` includes all reasoning tools and all Knowt tools
- [ ] `harnessiq/agents/__init__.py` exports `KnowtAgent` and `KnowtMemoryStore`
- [ ] `master_prompt.md` has clearly labeled `[TODO: ...]` sections for all domain-specific content
- [ ] `master_prompt.md` has complete static sections: Agent Guide, Environment, Operating Rules, Agent Memory explanation
- [ ] All tests pass with no linter or type errors

## Verification Steps
1. `ruff check harnessiq/agents/knowt/ harnessiq/agents/__init__.py`
2. `mypy harnessiq/agents/knowt/`
3. `pytest tests/test_knowt_agent.py -v --tb=short`
4. Smoke: `from harnessiq.agents import KnowtAgent` — verify importable
5. Smoke: instantiate with mock model and temp path, call `build_system_prompt()`, verify it returns non-empty string from file

## Dependencies
Ticket 2 (KnowtMemoryStore), Ticket 3 (create_knowt_tools), Ticket 1 (create_reasoning_tools).

## Drift Guard
This ticket must not modify `BaseAgent`, any tool module, or any existing agent. It must not add CLI commands. The master prompt must remain a `.md` file — it must not be hardcoded into the Python class.
