## Ticket 2 Quality Pipeline

### Stage 1 - Static Analysis

- Configured linter: none found in repository tooling.
- Manual action taken:
  - kept new selector and profile-resolution code fully annotated
  - kept the implementation additive under `harnessiq/toolset/` without changing runtime agent wiring
  - ran `python -m compileall harnessiq tests` to confirm syntax integrity across the repository
- Result: pass

Commands:

```powershell
python -m compileall harnessiq tests
```

### Stage 2 - Type Checking

- Configured type checker: none found in repository tooling.
- Manual action taken:
  - annotated all new public helpers and selector methods
  - validated protocol compatibility with `DynamicToolSelector` using runtime-checkable protocol assertions in tests
- Result: pass by annotated-code review

### Stage 3 - Unit Tests

Commands:

```powershell
pytest tests/test_toolset_dynamic_selector.py tests/test_toolset_registry.py tests/test_tool_selection_shared.py tests/test_interfaces.py -q
```

Observed result:

- `100 passed in 0.32s`

Result: pass

### Stage 4 - Integration & Contract Tests

Commands:

```powershell
pytest tests/test_toolset_factory.py tests/test_tools.py tests/test_sdk_package.py -q
```

Observed result:

- `54 passed, 3 warnings in 9.82s`

Notes:

- The warnings came from packaging/build tool dependencies already present in the repo test surface and were not introduced by this ticket.

Result: pass

### Stage 5 - Smoke & Manual Verification

Manual checks performed:

- Ran an isolated selector smoke script with a fake embedding backend and two tool profiles.
- Confirmed the selector chose `filesystem.read_text_file` for a file-inspection query.
- Confirmed scored output was deterministic and stayed inside the provided candidate profile set.

Commands:

```powershell
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

Observed result:

- selected keys: `('filesystem.read_text_file',)`
- scored tools: `(('filesystem.read_text_file', 1.0), ('records.save_output', 0.0))`

Result: pass
