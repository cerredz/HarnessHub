# Ticket 3: Knowt Tools Layer

## Title
Add `harnessiq/tools/knowt/` with five Knowt-specific tools including Creatify-backed `create_video`

## Intent
The Knowt agent needs a set of tools that manage its content creation pipeline. These tools enforce the agent's deterministic memory: `create_video` is gated behind script and avatar creation checks. All tools are backed by `KnowtMemoryStore` and follow the existing `harnessiq/tools/{provider}/` subfolder pattern.

## Scope
**In scope**:
- `harnessiq/tools/knowt/__init__.py` and `harnessiq/tools/knowt/operations.py`
- Five tools: `knowt.create_script`, `knowt.create_avatar_description`, `knowt.create_video`, `knowt.create_file`, `knowt.edit_file`
- Five new key constants in `harnessiq/shared/tools.py`
- `create_video` calls `create_lipsync_v2` on `CreatifyClient`
- Test coverage in `tests/test_knowt_tools.py`

**Out of scope**:
- The agent harness (ticket 4)
- Adding these tools to BUILTIN_TOOLS
- Creatify `CreatifyCredentials` loading (caller's responsibility)

## Relevant Files
| File | Change |
|------|--------|
| `harnessiq/tools/knowt/__init__.py` | New — re-exports from operations |
| `harnessiq/tools/knowt/operations.py` | New — all five tool implementations + factory |
| `harnessiq/shared/tools.py` | Modify — add five KNOWT_* constants and `__all__` entries |
| `tests/test_knowt_tools.py` | New — unit + integration tests |

## Approach

### Key constants (added to `harnessiq/shared/tools.py`)
```python
KNOWT_CREATE_SCRIPT = "knowt.create_script"
KNOWT_CREATE_AVATAR_DESCRIPTION = "knowt.create_avatar_description"
KNOWT_CREATE_VIDEO = "knowt.create_video"
KNOWT_CREATE_FILE = "knowt.create_file"
KNOWT_EDIT_FILE = "knowt.edit_file"
```

### Factory function signature
```python
def create_knowt_tools(
    *,
    memory_store: KnowtMemoryStore,
    creatify_client: CreatifyClient | None = None,
    creatify_credentials: CreatifyCredentials | None = None,
) -> tuple[RegisteredTool, ...]:
```
If both `creatify_client` and `creatify_credentials` are None, `create_video` is registered but will return a semantic error on invocation (no crash at registration time).

### Tool: `knowt.create_script`
- Required: `topic` (string), `angle` (string), `script_text` (string)
- Handler: writes `script_text` to `memory_store.write_script()`, appends creation log entry, returns `{"script": script_text, "stored_to": "current_script.md", "topic": topic, "angle": angle}`
- This is called AFTER the agent has reasoned through ideas with `reason.brainstorm`

### Tool: `knowt.create_avatar_description`
- Required: `script_text` (string), `avatar_style` (string)
- Optional: `target_audience` (string), `tone` (string)
- Handler: builds a structured chain-of-thought block from the inputs, then builds the avatar description, stores to `memory_store.write_avatar_description()`, appends creation log entry
- Returns: `{"chain_of_thought": "...", "avatar_description": "...", "stored_to": "current_avatar_description.md"}`
- CoT structure: "Based on script about [topic_keywords], targeting [target_audience], the avatar should exhibit [style] characteristics..."

### Tool: `knowt.create_video`
- Required: `script` (string), `avatar_id` (string), `voice_id` (string)
- Optional: `aspect_ratio` (string, default "9:16"), `name` (string), `background_url` (string)
- Memory guard (checked first): if `not memory_store.is_script_created()` OR `not memory_store.is_avatar_description_created()`, return semantic error:
  ```python
  {
      "error": "create_video cannot be called before both create_script and create_avatar_description have been completed.",
      "missing": ["create_script"] | ["create_avatar_description"] | ["create_script", "create_avatar_description"],
      "resolution": "Call knowt.create_script first, then knowt.create_avatar_description, then retry create_video."
  }
  ```
- If guard passes: calls `creatify_client.execute_operation("create_lipsync_v2", payload=payload)` where payload = `{"script": script, "avatar_id": avatar_id, "voice_id": voice_id, "aspect_ratio": aspect_ratio, ...}`
- Returns: `{"operation": "create_lipsync_v2", "response": <creatify_response>}`
- If no Creatify client configured: return `{"error": "No Creatify client configured. Pass creatify_credentials or creatify_client to create_knowt_tools()."}`

### Tool: `knowt.create_file`
- Required: `filename` (string), `content` (string)
- Handler: calls `memory_store.write_file(filename, content)`, returns `{"filename": filename, "path": str(path), "action": "created"}`

### Tool: `knowt.edit_file`
- Required: `filename` (string), `content` (string)
- Handler: calls `memory_store.edit_file(filename, content)`, returns `{"filename": filename, "path": str(path), "action": "edited"}`

## Assumptions
- `KnowtMemoryStore` (ticket 2) is available
- Creatify's `create_lipsync_v2` endpoint accepts: `script`, `avatar_id`, `voice_id`, `aspect_ratio` (known from operations catalog)
- Tool registration succeeds even when no Creatify client is provided (graceful degradation)
- Memory guard enforced via `memory_store.is_script_created()` / `is_avatar_description_created()` — file-backed state, consistent across process restarts

## Acceptance Criteria
- [ ] `harnessiq/tools/knowt/__init__.py` and `operations.py` exist
- [ ] Five KNOWT_* constants defined in `shared/tools.py` and in `__all__`
- [ ] All five tools registered in the tuple returned by `create_knowt_tools()`
- [ ] `create_script` stores script to `current_script.md` and `is_script_created()` returns True afterward
- [ ] `create_avatar_description` stores to `current_avatar_description.md`, returns `chain_of_thought` + `avatar_description`
- [ ] `create_video` returns semantic error dict (not raises) when script or avatar description not created
- [ ] `create_video` calls `creatify_client.execute_operation("create_lipsync_v2", payload=...)` when prerequisites met
- [ ] `create_file` and `edit_file` write to memory directory only (path guard enforced)
- [ ] No Creatify client → `create_video` returns config error dict
- [ ] All tests pass with no linter or type errors

## Verification Steps
1. `ruff check harnessiq/tools/knowt/ harnessiq/shared/tools.py`
2. `mypy harnessiq/tools/knowt/`
3. `pytest tests/test_knowt_tools.py -v --tb=short`
4. Smoke memory guard: instantiate without Creatify client, call `create_video` → verify semantic error dict returned

## Dependencies
Ticket 2 (KnowtMemoryStore must exist).

## Drift Guard
This ticket must not modify any existing tool module, add tools to BUILTIN_TOOLS, or create the agent harness. It must not import from `harnessiq.agents`. The `create_video` memory guard must return an error dict (not raise) to match BaseAgent's exception handling pattern.
