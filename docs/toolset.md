# Toolset

Harnessiq ships a plug-and-play toolset API that mirrors the `master_prompts` interface: call a function, get back a ready-to-use object.

## Retrieve a built-in tool by key

```python
from harnessiq.toolset import get_tool

brainstorm = get_tool("reason.brainstorm")

result = brainstorm.execute({"topic": "AI product strategy"})
print(result.output["reasoning_instruction"])
```

## Retrieve multiple tools by key

```python
from harnessiq.toolset import get_tools

core_reasoning = get_tools(
    "reason.brainstorm",
    "reason.chain_of_thought",
    "reason.critique",
)
```

## Retrieve an entire tool family

```python
from harnessiq.toolset import get_family

# All 50 reasoning lens tools
reasoning_lenses = get_family("reasoning")

# First 4 tools in catalog order
four_lenses = get_family("reasoning", count=4)

# All filesystem tools
filesystem = get_family("filesystem")
```

Available built-in families: `core`, `context`, `text`, `records`, `control`, `prompt`, `filesystem`, `reason` (3 core reasoning tools), `reasoning` (50 cognitive lens tools).

## List all available tools

```python
from harnessiq.toolset import list_tools

for entry in list_tools():
    status = "requires credentials" if entry.requires_credentials else "ready to use"
    print(f"{entry.key}  [{entry.family}]  {status}")
```

## Retrieve a provider tool

Provider tools connect to external APIs and require a credentials object.

```python
from harnessiq.toolset import get_tool
from harnessiq.providers.creatify import CreatifyCredentials

creatify = get_tool(
    "creatify.request",
    credentials=CreatifyCredentials(api_id="...", api_key="..."),
)
```

Available provider families: `arcads`, `coresignal`, `creatify`, `exa`, `instantly`, `leadiq`, `lemlist`, `outreach`, `peopledatalabs`, `phantombuster`, `proxycurl`, `resend`, `salesforge`, `snovio`, `zoominfo`.

## Create a custom tool with `define_tool()`

```python
from harnessiq.toolset import define_tool


def shout(args):
    return args["text"].upper()


shout_tool = define_tool(
    key="custom.shout",
    description="Convert text to uppercase. Use when you need to emphasise output.",
    parameters={
        "text": {
            "type": "string",
            "description": "The text to convert to uppercase.",
        }
    },
    required=["text"],
    handler=shout,
)
```

The `parameters` dict maps directly to JSON Schema `properties`. The `required` list names which parameters must be present. `additional_properties=True` relaxes the schema to allow extra keys.

## Create a custom tool with the `@tool` decorator

```python
from harnessiq.toolset import tool


@tool(
    key="custom.word_count",
    description="Count the number of words in a text string.",
    parameters={
        "text": {
            "type": "string",
            "description": "The text to count words in.",
        }
    },
    required=["text"],
)
def word_count(args):
    return {"count": len(args["text"].split())}


# word_count is now a RegisteredTool.
result = word_count.execute({"text": "hello world"})
print(result.output)  # {"count": 2}
```

The decorated function is replaced by the `RegisteredTool` directly — the original callable is preserved as the tool's handler.

## Compose tools into a registry for use in an agent

```python
from harnessiq.toolset import define_tool, get_family
from harnessiq.tools import ToolRegistry
from harnessiq.agents import BaseAgent, AgentParameterSection


def my_handler(args):
    return args["query"].strip().lower()


search_normalizer = define_tool(
    key="custom.normalize_query",
    description="Normalise a search query to lowercase with no surrounding whitespace.",
    parameters={"query": {"type": "string", "description": "The raw search query."}},
    required=["query"],
    handler=my_handler,
)

registry = ToolRegistry([
    *get_family("reason"),       # brainstorm, chain_of_thought, critique
    *get_family("filesystem"),   # read, write, list, etc.
    search_normalizer,           # your custom tool
])


class MyAgent(BaseAgent):
    def build_system_prompt(self) -> str:
        return "You are a research assistant."

    def load_parameter_sections(self) -> list[AgentParameterSection]:
        return [AgentParameterSection(title="Goal", content="Research the given topic.")]
```

Pass `tool_executor=registry` when constructing the agent.

## Top-level access

The `toolset` module is also accessible via the top-level `harnessiq` namespace:

```python
import harnessiq

brainstorm = harnessiq.toolset.get_tool("reason.brainstorm")
```
