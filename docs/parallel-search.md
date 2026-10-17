# Parallel web search with OpenAI Responses

Use Harnessiq's OpenAI request builders to attach [Parallel Search MCP](https://docs.parallel.ai/integrations/mcp/search-mcp) to a Responses API request. It provides `web_search` for current information and `web_fetch` for reading specific pages. Anonymous search uses Fast mode and needs no Parallel account or API key; the free tier has usage limits.

This recipe uses OpenAI's hosted [remote MCP support](https://developers.openai.com/api/docs/guides/tools-remote-mcp). OpenAI connects to Parallel over HTTP and executes the MCP tools. These tools belong to this Responses request, rather than Harnessiq's local `ToolRegistry` or a harness's `tools=` injection surface.

## Build the request

From the repository root, install the SDK:

```bash
pip install -e .
```

Set `OPENAI_MODEL` to a model available to your OpenAI account that supports remote MCP. Request construction needs no API key and sends no network requests:

```python
import json
import os

from harnessiq.providers.openai import (
    OpenAIResponseRequestDTO,
    build_mcp_tool,
    build_response_request,
)

parallel_search = build_mcp_tool(
    server_label="parallel_search",
    server_url="https://search.parallel.ai/mcp",
    headers={"User-Agent": "Harnessiq/0.1.0 (Parallel Search MCP recipe)"},
    allowed_tools=("web_search", "web_fetch"),
    require_approval="never",
)

request = OpenAIResponseRequestDTO(
    model_name=os.environ["OPENAI_MODEL"],
    input_items=(
        "Search for the latest stable Python release, fetch its official "
        "what's new page, and summarize two changes with source URLs."
    ),
    tools=(parallel_search,),
    max_output_tokens=1500,
)

print(json.dumps(build_response_request(request), indent=2))
```

The allowlist exposes only search and page fetching. `require_approval="never"` lets OpenAI send tool calls to Parallel without a separate approval exchange. Use this setting for public queries and URLs you intend to share with Parallel; applications that need per-call consent should implement the approval flow in the OpenAI guide instead.

## Send the request

Set `OPENAI_API_KEY` in your environment, then run this after the request-building code above. OpenAI API access and model usage are separate from Parallel's anonymous MCP access. No additional OpenAI Python client package is needed:

```python
from harnessiq.providers.openai import OpenAIClient

client = OpenAIClient(
    api_key=os.environ["OPENAI_API_KEY"],
    timeout_seconds=120.0,
)
response = client.create_response(request)
print(json.dumps(response, indent=2))
```

The client returns the raw Responses API JSON. Inspect its `output` array for `mcp_list_tools`, any `mcp_call` items and their errors, and the final `message` text. Tool selection is model-driven, so a response without a successful `mcp_call` does not establish that search or fetching ran. If a call fails, inspect its error before relying on the answer; anonymous usage limits may require retrying later or configuring authenticated access as described in the Parallel guide.

To make a request without Parallel, omit `tools=(parallel_search,)` when constructing the DTO. The configuration above applies only to the request that includes it.
