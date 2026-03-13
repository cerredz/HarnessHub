# Ticket Index

1. Ticket 1: Add shared HTTP transport and expand the OpenAI provider client surface
   Issue: #9
   URL: https://github.com/cerredz/HarnessHub/issues/9
   PR: https://github.com/cerredz/HarnessHub/pull/15
   Status: implemented on branch `issue-9`
   Description: Introduce shared request execution primitives and reorganize OpenAI into a real client/helper package with broad tool support.
   Dependency: none

2. Ticket 2: Expand the Grok provider with xAI chat, search, collections, and MCP helpers
   Issue: #10
   URL: https://github.com/cerredz/HarnessHub/issues/10
   Description: Build the xAI/Grok client and tool builders on top of the shared transport and OpenAI-compatible patterns.
   Dependency: Ticket 1

3. Ticket 3: Expand the Anthropic provider with Messages, server tools, MCP, and token counting helpers
   Issue: #11
   URL: https://github.com/cerredz/HarnessHub/issues/11
   Description: Add an Anthropic-native client/helper surface for messages, token counting, server tools, and MCP configuration.
   Dependency: Ticket 1

4. Ticket 4: Expand the Gemini provider with content, tool, grounding, caching, and file-search helpers
   Issue: #12
   URL: https://github.com/cerredz/HarnessHub/issues/12
   Description: Add a Gemini-native client/helper surface for generate-content, count-tokens, grounding tools, file search, and caching.
   Dependency: Ticket 1

Phase 3a complete
Phase 3 complete
