# Ticket 3: Move path constants to shared; refactor KnowtAgent to accept tools/config as params; add memory_path to BaseAgent

## Intent
Addresses PR comments 1 and 2:
1. `_PROMPTS_DIR`/`_MASTER_PROMPT_PATH` path constants should live in shared (as string pieces)
2. Tools should be injected as constructor params (not hard-coded inside __init__)
3. Config should be a constructor param, not built internally
4. Memory stores should be a BaseAgent-level concept

## Scope
**Changes**: `harnessiq/shared/knowt.py`, `harnessiq/agents/base.py`, `harnessiq/agents/knowt/agent.py`, `tests/test_knowt_agent.py`, `tests/test_agents_base.py`
**No touch**: knowt tools, shared/tools.py, providers

## Relevant Files
- `harnessiq/shared/knowt.py` — add `PROMPTS_DIRNAME = "prompts"` and `MASTER_PROMPT_FILENAME = "master_prompt.md"`
- `harnessiq/agents/base.py` — add `memory_path: Path | None = None` parameter; store as `self._memory_path`; add `memory_path` property
- `harnessiq/agents/knowt/agent.py` — import string constants from shared; add `tools: Sequence[RegisteredTool] | None` and `config: KnowtAgentConfig | None` parameters; pass `memory_path` to super().__init__; update internal tool factory to use `create_injectable_reasoning_tools`
- `tests/test_knowt_agent.py` — update to verify new optional params work; update tool count assertion (3 injectable + 5 knowt = 8, same)
- `tests/test_agents_base.py` — add coverage for `memory_path` param on BaseAgent

## Approach

### shared/knowt.py
Add two string constants near the filename constants:
```python
PROMPTS_DIRNAME = "prompts"
MASTER_PROMPT_FILENAME = "master_prompt.md"
```

### agents/base.py
Add `memory_path: Path | None = None` parameter to `__init__`; store as `self._memory_path`; add property.

### agents/knowt/agent.py
```python
from harnessiq.shared.knowt import MASTER_PROMPT_FILENAME, PROMPTS_DIRNAME

_PROMPTS_DIR = Path(__file__).parent / PROMPTS_DIRNAME
_MASTER_PROMPT_PATH = _PROMPTS_DIR / MASTER_PROMPT_FILENAME

class KnowtAgent(BaseAgent):
    def __init__(
        self, *, model, memory_path, tools=None, config=None,
        creatify_client=None, creatify_credentials=None,
        max_tokens=DEFAULT_AGENT_MAX_TOKENS, reset_threshold=DEFAULT_AGENT_RESET_THRESHOLD,
    ):
        config = config or KnowtAgentConfig(...)
        self._config = config
        self._memory_store = KnowtMemoryStore(...)
        self._memory_store.prepare()
        if tools is None:
            tools = [*create_injectable_reasoning_tools(), *create_knowt_tools(...)]
        tool_registry = ToolRegistry(tools)
        super().__init__(
            ..., memory_path=self._config.memory_path
        )
```

Tools are still built by default (backward compat) but can be overridden. Config is now an accepted parameter.

## Acceptance Criteria
- [ ] `PROMPTS_DIRNAME` and `MASTER_PROMPT_FILENAME` in `shared/knowt.py`
- [ ] `BaseAgent` has `memory_path` parameter and property
- [ ] `KnowtAgent.__init__` accepts `tools: Sequence[RegisteredTool] | None`
- [ ] `KnowtAgent.__init__` accepts `config: KnowtAgentConfig | None`
- [ ] `KnowtAgent(model=m, memory_path=p)` still works (backward compat)
- [ ] `KnowtAgent(model=m, memory_path=p, tools=[...], config=cfg)` works
- [ ] All 24 existing knowt agent tests pass
- [ ] BaseAgent tests cover new `memory_path` param

## Dependencies
Ticket 1 (for `create_injectable_reasoning_tools`), Ticket 2 (for `FILES_CREATE_FILE`)
