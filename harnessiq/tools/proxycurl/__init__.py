"""Proxycurl MCP-style tool factory.

NOTE: Proxycurl shut down in January 2025 following a LinkedIn lawsuit.
This package is preserved for reference only.
"""

from harnessiq.tools.proxycurl.operations import (
    build_proxycurl_request_tool_definition,
    create_proxycurl_tools,
)

__all__ = [
    "build_proxycurl_request_tool_definition",
    "create_proxycurl_tools",
]
