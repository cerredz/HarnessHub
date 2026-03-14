# Tools Example

Harnessiq ships a built-in tool registry that combines the reusable tool families in the SDK.

```python
from harnessiq.tools import ECHO_TEXT, TEXT_NORMALIZE_WHITESPACE, create_builtin_registry

registry = create_builtin_registry()

echo = registry.execute(ECHO_TEXT, {"text": "hello"})
normalized = registry.execute(TEXT_NORMALIZE_WHITESPACE, {"text": "  too   much   space  "})

print(echo.output)
print(normalized.output)
```

You can also compose your own registry from selected tool families:

```python
from harnessiq.tools import ToolRegistry, create_filesystem_tools, create_general_purpose_tools

registry = ToolRegistry(
    [
        *create_general_purpose_tools(),
        *create_filesystem_tools(),
    ]
)
```
