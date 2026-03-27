## Ticket 2 Self-Critique

### Findings

1. The first implementation accepted catalog-entry overrides only as a mapping.
   - Why this mattered:
     - The existing toolset registry already exposes catalog metadata as `list[ToolEntry]`.
     - Forcing callers to reshape that list into a dictionary adds avoidable friction to the profile-resolution path.
   - Improvement made:
     - Updated `resolve_tool_profiles()` to accept either a mapping or a sequence of `ToolEntry` records.
     - Added a targeted test covering the sequence form.

2. The new selector surface was public from `harnessiq.toolset`, but the SDK packaging smoke test did not lock that API in.
   - Why this mattered:
     - Public export drift is easiest to miss when the wheel still builds successfully.
     - The feature will be used from the package surface, not only from internal module paths.
   - Improvement made:
     - Extended `tests/test_sdk_package.py` to assert `DefaultDynamicToolSelector` and `resolve_tool_profiles` are available from `harnessiq.toolset` in the built package.

### Post-Critique Verification

Re-ran the full ticket verification surface after the refinement:

```powershell
pytest tests/test_toolset_dynamic_selector.py tests/test_toolset_registry.py tests/test_tool_selection_shared.py tests/test_interfaces.py -q
pytest tests/test_toolset_factory.py tests/test_tools.py tests/test_sdk_package.py -q
python -m compileall harnessiq tests
@'
from harnessiq.shared.tool_selection import ToolProfile, ToolSelectionConfig
from harnessiq.toolset import DefaultDynamicToolSelector

class FakeBackend:
    def embed_texts(self, texts):
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append((
                float(lowered.count('read') + lowered.count('file')),
                float(lowered.count('save') + lowered.count('write')),
            ))
        return tuple(vectors)

selector = DefaultDynamicToolSelector(
    config=ToolSelectionConfig(enabled=True, top_k=1),
    embedding_backend=FakeBackend(),
)
profiles = (
    ToolProfile(
        key='filesystem.read_text_file',
        name='read_text_file',
        family='filesystem',
        description='Read a UTF-8 text file.',
        semantic_description='Read file contents from disk.',
        tags=('filesystem', 'read', 'file'),
        when_to_use='Use when the agent needs to inspect a file.',
    ),
    ToolProfile(
        key='records.save_output',
        name='save_output',
        family='records',
        description='Persist a validated output record.',
        semantic_description='Write or save durable records.',
        tags=('records', 'save', 'write'),
        when_to_use='Use when the agent needs to persist results.',
    ),
)
result = selector.select(
    context_window=[{'kind': 'user', 'content': 'Read the file and inspect its contents.'}],
    candidate_profiles=profiles,
)
print(result.selected_keys)
print(result.scored_tools)
'@ | python -
```

Observed results:

- `101 passed in 0.33s`
- `54 passed, 3 warnings in 7.71s`
- `compileall` passed
- smoke selector output remained:
  - `('filesystem.read_text_file',)`
  - `(('filesystem.read_text_file', 1.0), ('records.save_output', 0.0))`

### Conclusion

The refined ticket-2 branch now:

- derives retrieval profiles from existing tool metadata without catalog mutation
- supports additive custom tools and override metadata
- exposes a stable public selector surface through `harnessiq.toolset`
- keeps the implementation isolated from agent runtime wiring
