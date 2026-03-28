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
from harnessiq.tools import create_filesystem_tools, create_general_purpose_tools, create_tool_registry

registry = create_tool_registry(
    create_general_purpose_tools(),
    create_filesystem_tools(),
)
```

For custom tools, the ergonomic path is `harnessiq.toolset.define_tool()` plus an additive `tools=` injection into a concrete harness:

```python
from harnessiq.agents import LinkedInJobApplierAgent
from harnessiq.toolset import define_tool

resume_tool = define_tool(
    key="custom.resume_summary",
    description="Summarize the candidate resume before applying.",
    parameters={},
    handler=lambda arguments: {"summary": "Staff-level platform engineer."},
)

agent = LinkedInJobApplierAgent(
    model=model,
    browser_tools=my_browser_tools,
    tools=(resume_tool,),
)
```

Provider-backed tools follow the same pattern. For example, Apollo is exposed as one MCP-style request tool whose `operation` argument selects the API endpoint:

```python
from harnessiq.providers.apollo.client import ApolloCredentials
from harnessiq.tools.apollo import create_apollo_tools

apollo_tools = create_apollo_tools(
    credentials=ApolloCredentials(api_key="apollo_..."),
    allowed_operations=("search_people", "search_organizations", "enrich_person"),
)
```

This returns a `RegisteredTool` keyed as `apollo.request`, ready to drop into a `ToolRegistry` or a concrete agent harness such as `LeadsAgent`.

Browser Use follows the same provider-backed pattern:

```python
from harnessiq.shared.credentials import BrowserUseCredentials
from harnessiq.tools.browser_use import create_browser_use_tools

browser_use_tools = create_browser_use_tools(
    credentials=BrowserUseCredentials(api_key="bu_..."),
    allowed_operations=(
        "create_task",
        "get_task_status",
        "create_session",
        "list_profiles",
        "execute_skill",
    ),
)
```

This returns a `RegisteredTool` keyed as `browser_use.request`. Inject it through an agent's additive `tools=` surface when you want coarse-grained Browser Use Cloud automation. It is not a drop-in replacement for the selector-driven `browser_tools` factories used by the current Playwright-backed LinkedIn and prospecting harnesses.

## Dynamic Selection

Harnessiq now supports an optional dynamic tool-selection layer on top of the existing static tool surface. The feature narrows what the model sees per turn; it does not replace the tool catalog or expand execution authority.

- static path: the agent exposes its normal runtime tool surface
- dynamic path: the agent exposes a per-turn subset selected from that existing surface
- `allowed_tools`: still acts as the execution ceiling when configured

This means you do not rewrite the tool catalog to use dynamic selection. Existing built-in tools, provider-backed request tools, and additive custom tools all continue to be registered the same way. The selector works from the live tool definitions already attached to the agent runtime.

For configuration examples and the CLI surface, see [docs/dynamic-tool-selection.md](./dynamic-tool-selection.md).
